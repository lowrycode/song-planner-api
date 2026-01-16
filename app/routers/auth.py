import os
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models import User, RefreshToken, UserRole, Church, Network
from app.schemas.auth import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginResponse,
    UserLogoutResponse,
    UserMeResponse,
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
from app.dependencies import require_min_role, get_current_user

router = APIRouter()

IS_DEV = os.getenv("IS_DEV", False)
SECURE = not IS_DEV  # Used for defining HTTP-only cookies


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


@router.post("/login", response_model=UserLoginResponse)
def login(
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form.username).first()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if user.role == UserRole.unapproved:
        raise HTTPException(status_code=403, detail="User account not approved")

    # Create tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token()
    refresh_hash = hash_token(refresh_token)

    # Store refresh token in DB
    db_token = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(db_token)
    db.commit()

    # Set HttpOnly, Secure cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=SECURE,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth/refresh",  # Restrict path to refresh endpoint
    )

    return {"message": "Login successful"}


@router.post("/refresh")
def refresh_token(
    response: Response,
    refresh_token: str = Cookie(...),
    db: Session = Depends(get_db),
):
    refresh_hash = hash_token(refresh_token)

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

    # Revoke old refresh token
    db_token.revoked = True

    new_refresh = create_refresh_token()
    new_refresh_hash = hash_token(new_refresh)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=new_refresh_hash,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.commit()

    # Create new access token
    new_access = create_access_token({"sub": str(user.id)})

    # Set new cookies
    response.set_cookie(
        key="access_token",
        value=new_access,
        httponly=True,
        secure=SECURE,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth/refresh",
    )

    return {"message": "Tokens refreshed"}


@router.post("/logout", response_model=UserLogoutResponse)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    if refresh_token:
        refresh_hash = hash_token(refresh_token)
        db_token = (
            db.query(RefreshToken)
            .filter(RefreshToken.token_hash == refresh_hash)
            .first()
        )

        if db_token:
            db_token.revoked = True
            db.commit()

    # Always clear cookies
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/auth/refresh")

    return {"message": "Logged out"}


@router.post("/change-password", response_model=ChangePasswordResponse)
def change_password(
    data: ChangePasswordRequest,
    response: Response,
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

    # Revoke ALL refresh tokens (all devices)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,
    ).update({"revoked": True})

    db.commit()

    # Clear cookies for current device
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth/refresh")

    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserMeResponse)
def get_me(user: User = Depends(get_current_user)):
    """
    Returns info about the currently authenticated user based on access_token cookie.
    """
    return UserMeResponse(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        role=UserRole(user.role).name,
    )
