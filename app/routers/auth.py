from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models import User, RefreshToken
from app.schemas.auth import (
    UserRegisterRequest,
    UserRegisterResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLogoutRequest,
    UserLogoutResponse,
)
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    hash_token,
    hash_password,
    verify_password,
)
from app.settings import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/register", status_code=201, response_model=UserRegisterResponse)
def register_user(data: UserRegisterRequest, db: Session = Depends(get_db)):
    # Check if username exists
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    # Hash password
    hashed_pw = hash_password(data.password)

    # Create user
    new_user = User(username=data.username, hashed_password=hashed_pw)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully", "user_id": new_user.id}


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # --- Create tokens ---
    access = create_access_token({"sub": user.username})
    refresh = create_refresh_token()
    refresh_hash = hash_token(refresh)

    # --- Store in DB ---
    db_token = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(db_token)
    db.commit()

    return {"access_token": access, "refresh_token": refresh}


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    refresh_hash = hash_token(request.refresh_token)

    db_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == refresh_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db_token.user

    # -------- ROTATION --------
    db_token.revoked = True  # invalidate old token

    new_refresh = create_refresh_token()
    new_hash = hash_token(new_refresh)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=new_hash,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )

    db.commit()

    # issue new access token
    new_access = create_access_token({"sub": user.username})

    return {"access_token": new_access, "refresh_token": new_refresh}


@router.post("/logout", response_model=UserLogoutResponse)
def logout(request: UserLogoutRequest, db: Session = Depends(get_db)):
    refresh_hash = hash_token(request.refresh_token)
    db_token = (
        db.query(RefreshToken).filter(RefreshToken.token_hash == refresh_hash).first()
    )

    if db_token:
        db_token.revoked = True
        db.commit()

    return {"message": "Logged out"}
