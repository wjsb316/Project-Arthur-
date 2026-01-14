from datetime import datetime, timedelta, timezone
from typing import Any, Union
import hashlib
import base64

from jose import jwt
from passlib.context import CryptContext

# These should be loaded from settings/env in a real app
SECRET_KEY = "your-secret-key-change-me"  # TODO: Move to config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _prepare_password(password: str) -> str:
    """
    Pre-hash the password with SHA-256 to support passwords longer than 72 bytes
    (bcrypt limit) and ensure consistent handling.
    """
    # SHA-256 produces 32 bytes
    hashed_bytes = hashlib.sha256(password.encode("utf-8")).digest()
    # We hex encode it which results in 64 characters (bytes). 
    # 64 chars is < 72 chars, so this is safe for bcrypt.
    return hashed_bytes.hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # WARNING: Plain text comparison - INSECURE for production
    return plain_password == hashed_password


def get_password_hash(password: str) -> str:
    # WARNING: Returning plain text - INSECURE for production
    return password


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
