from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole
from app.utils.auth import verify_access_token


# The OAuth2PasswordBearer dependency checks the authorization header
# (expects format 'Authorization: Bearer <JWT>') and
# - if found: returns raw JWT
# - if not found: raises HTTPException (401 Not authenticated)
# with response header 'WWW-Authenticate: Bearer'
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# --- Authentication ---
def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    Used to verify identity and that user exists in DB.
    """
    # JWT to verify identity
    payload = verify_access_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    # Check user still exists in the database
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=403, detail="User no longer exists")

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
