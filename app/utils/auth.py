import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi import HTTPException, status
from app.settings import settings
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# -------- PASSWORD ----------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


# -------- ACCESS TOKEN ----------
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# -------- REFRESH TOKEN ----------
def create_refresh_token():
    return secrets.token_hex(32)


def hash_token(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


# -------- VERIFY ACCESS TOKEN ----------
def verify_access_token(token: str):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
