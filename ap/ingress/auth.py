import logging
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import timedelta

from ..database import get_db
from ..models.users import User
from ..security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_password_hash,
    verify_password,
)

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class UserCreate(BaseModel):
    username: str
    password: str
    user_id: Optional[str] = None


class UserResponse(BaseModel):
    user_id: str
    username: str
    created_at: str
    voice_characters_used: int = 0


class Token(BaseModel):
    access_token: str
    token_type: str


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Use SQLAlchemy select
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    return user


def build_auth_router() -> APIRouter:
    router = APIRouter(tags=["auth"])

    @router.post("/token", response_model=Token)
    async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        session: Annotated[AsyncSession, Depends(get_db)],
    ):
        stmt = select(User).where(User.username == form_data.username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(form_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}

    @router.post("/register", response_model=UserResponse)
    async def register(
        user: UserCreate,
        session: Annotated[AsyncSession, Depends(get_db)],
    ):
        try:
            stmt = select(User).where(User.username == user.username)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered",
                )
            
            import uuid
            user_id = user.user_id or str(uuid.uuid4())
            hashed_password = get_password_hash(user.password)
            
            new_user = User(
                user_id=user_id,
                username=user.username,
                password_hash=hashed_password
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            
            return UserResponse(
                user_id=new_user.user_id,
                username=new_user.username,
                created_at=str(new_user.created_at),
                voice_characters_used=getattr(new_user, "voice_characters_used", 0),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Registration failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registration failed: {str(e)}"
            )

    @router.get("/users/me", response_model=UserResponse)
    async def read_me(
        current_user: Annotated[User, Depends(get_current_user)],
    ):
        return UserResponse(
            user_id=current_user.user_id,
            username=current_user.username,
            created_at=str(current_user.created_at),
            voice_characters_used=getattr(current_user, "voice_characters_used", 0),
        )

    @router.delete("/users/me")
    async def delete_me(
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_db)],
    ):
        await session.delete(current_user)
        await session.commit()
        return {"msg": "User deleted"}

    return router
