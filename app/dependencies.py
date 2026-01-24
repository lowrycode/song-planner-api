from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    User,
    UserRole,
    UserNetworkAccess,
    UserChurchAccess,
    UserChurchActivityAccess,
    Church,
    ChurchActivity,
)
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


def get_allowed_church_activity_ids(
    user: User = Depends(require_min_role(UserRole.normal)),
    db: Session = Depends(get_db),
) -> set[int]:
    allowed_activity_ids = set()

    # Network access
    network_ids = db.scalars(
        select(UserNetworkAccess.network_id).where(UserNetworkAccess.user_id == user.id)
    ).all()

    if network_ids:
        activities_from_networks = db.scalars(
            select(ChurchActivity.id)
            .join(Church, Church.id == ChurchActivity.church_id)
            .where(Church.network_id.in_(network_ids))
        ).all()
        allowed_activity_ids.update(activities_from_networks)

    # Church access
    church_ids = db.scalars(
        select(UserChurchAccess.church_id).where(UserChurchAccess.user_id == user.id)
    ).all()

    if church_ids:
        activities_from_churches = db.scalars(
            select(ChurchActivity.id).where(ChurchActivity.church_id.in_(church_ids))
        ).all()
        allowed_activity_ids.update(activities_from_churches)

    # Direct activity access
    direct_activity_ids = db.scalars(
        select(UserChurchActivityAccess.church_activity_id).where(
            UserChurchActivityAccess.user_id == user.id
        )
    ).all()

    allowed_activity_ids.update(direct_activity_ids)

    return allowed_activity_ids
