from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole
from app.utils.auth import verify_access_token


# --- Authentication ---
def get_current_user(
    access_token: str = Cookie(None), db: Session = Depends(get_db)
) -> User:
    """
    Used to verify identity and that user exists in DB.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    # JWT to verify identity
    payload = verify_access_token(access_token)
    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    return user


# --- Authorization ---
def require_min_role(min_role: UserRole):
    """
    Returns a dependency that verifies the user's role meets the minimum required role.
    """

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role < min_role:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return dependency
