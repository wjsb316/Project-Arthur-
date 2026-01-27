from typing import List, Optional
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from ..database import get_db
from ..models import User, Guardrail
from ..ingress.auth import get_current_user
from ..utils.embedding_factory import embedding_factory

logger = logging.getLogger("arthur.ap.ingress.guardrails")

router = APIRouter(prefix="/api/guardrails", tags=["guardrails"])

# Pydantic models
class GuardrailCreate(BaseModel):
    name: str
    prompt: str

class GuardrailUpdate(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None

class GuardrailResponse(BaseModel):
    id: int
    user_id: str
    name: str
    prompt: str
    created_at: str

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj: Guardrail):
        return cls(
            id=obj.id,
            user_id=obj.user_id,
            name=obj.name,
            prompt=obj.prompt,
            created_at=obj.created_at.isoformat()
        )

# Routes

@router.get("/", response_model=List[GuardrailResponse])
async def list_guardrails(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Guardrail).where(Guardrail.user_id == user.user_id)
    result = await db.execute(stmt)
    guardrails = result.scalars().all()
    return [GuardrailResponse.from_orm(guardrail) for guardrail in guardrails]

@router.post("/", response_model=GuardrailResponse)
async def create_guardrail(
    guardrail_in: GuardrailCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_guardrail = Guardrail(
        user_id=user.user_id,
        name=guardrail_in.name,
        prompt=guardrail_in.prompt
    )
    db.add(new_guardrail)
    await db.commit()
    await db.refresh(new_guardrail)
    
    # Generate embedding and store in vector table
    try:
        # Combine name and prompt for embedding
        embedding_text = f"{guardrail_in.name}: {guardrail_in.prompt}"
        embedding = embedding_factory.get_embedding(embedding_text)
        embedding_json = json.dumps(embedding)
        
        await db.execute(
            text("INSERT INTO guardrail_vectors(id, embedding) VALUES (:id, :embedding)"),
            {"id": new_guardrail.id, "embedding": embedding_json}
        )
        await db.commit()
        logger.info(f"Stored guardrail vector for guardrail {new_guardrail.id}")
    except Exception as e:
        logger.error(f"Failed to store guardrail vector: {e}")
        # Don't fail the whole operation if vector storage fails
    
    return GuardrailResponse.from_orm(new_guardrail)

@router.put("/{guardrail_id}", response_model=GuardrailResponse)
async def update_guardrail(
    guardrail_id: int,
    guardrail_update: GuardrailUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Guardrail).where(Guardrail.id == guardrail_id, Guardrail.user_id == user.user_id)
    result = await db.execute(stmt)
    guardrail = result.scalar_one_or_none()
    
    if not guardrail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guardrail not found"
        )
        
    if guardrail_update.name is not None:
        guardrail.name = guardrail_update.name
    if guardrail_update.prompt is not None:
        guardrail.prompt = guardrail_update.prompt
        
    await db.commit()
    await db.refresh(guardrail)
    
    # Update the vector embedding
    try:
        embedding_text = f"{guardrail.name}: {guardrail.prompt}"
        embedding = embedding_factory.get_embedding(embedding_text)
        embedding_json = json.dumps(embedding)
        
        # Delete old vector and insert new one
        await db.execute(
            text("DELETE FROM guardrail_vectors WHERE id = :id"),
            {"id": guardrail_id}
        )
        await db.execute(
            text("INSERT INTO guardrail_vectors(id, embedding) VALUES (:id, :embedding)"),
            {"id": guardrail_id, "embedding": embedding_json}
        )
        await db.commit()
        logger.info(f"Updated guardrail vector for guardrail {guardrail_id}")
    except Exception as e:
        logger.error(f"Failed to update guardrail vector: {e}")
    
    return GuardrailResponse.from_orm(guardrail)

@router.delete("/{guardrail_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guardrail(
    guardrail_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Guardrail).where(Guardrail.id == guardrail_id, Guardrail.user_id == user.user_id)
    result = await db.execute(stmt)
    guardrail = result.scalar_one_or_none()
    
    if not guardrail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guardrail not found"
        )
    
    # Delete from vector table first
    try:
        await db.execute(
            text("DELETE FROM guardrail_vectors WHERE id = :id"),
            {"id": guardrail_id}
        )
    except Exception as e:
        logger.error(f"Failed to delete guardrail vector: {e}")
        
    await db.delete(guardrail)
    await db.commit()
    return None

def build_guardrails_router() -> APIRouter:
    return router
