from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models import User, RefreshToken, UserRole, Church, Network
from app.schemas.auth import (
    UserRegisterRequest,
    UserRegisterResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLogoutRequest,
    UserLogoutResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
)
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    hash_token,
    hash_password,
    verify_password,
)
from app.settings import settings
from app.dependencies import require_min_role

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/register", status_code=201, response_model=UserRegisterResponse)
def register_user(data: UserRegisterRequest, db: Session = Depends(get_db)):
    # Check if username exists
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    # Check passwords match
    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    # Validate network + church relationship
    if not db.query(Network).filter(Network.id == data.network_id).first():
        raise HTTPException(404, "Network does not exist")

    if not db.query(Church).filter(Church.id == data.church_id).first():
        raise HTTPException(404, "Church does not exist")

    if (
        not db.query(Church)
        .filter(
            Church.id == data.church_id,
            Church.network_id == data.network_id,
        )
        .first()
    ):
        raise HTTPException(400, "Church does not belong to network")

    # Hash password
    hashed_pw = hash_password(data.password)

    # Create user
    new_user = User(
        username=data.username,
        hashed_password=hashed_pw,
        first_name=data.first_name,
        last_name=data.last_name,
        network_id=data.network_id,
        church_id=data.church_id,
        role=UserRole.unapproved,
    )

    db.add(new_user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid network or church",
        )

    db.refresh(new_user)

    return {"message": "User registered successfully", "user_id": new_user.id}


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # --- Create tokens ---
    access = create_access_token({"sub": str(user.id)})
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


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
)
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
):
    # Verify current password
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Prevent reusing the same password
    if verify_password(data.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="New password must be different from the current password",
        )

    if data.new_password != data.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    # Hash and save new password
    user.hashed_password = hash_password(data.new_password)

    # Revoke all existing refresh tokens for this user
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,
    ).update({"revoked": True})

    db.commit()

    return {"message": "Password changed successfully"}
