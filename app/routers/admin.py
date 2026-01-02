from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    User,
    UserRole,
    Network,
    Church,
    UserNetworkAccess,
    UserChurchAccess,
)
from app.schemas.admin import (
    GrantNetworkAccessResponse,
    GrantChurchAccessResponse,
)
from app.dependencies import require_min_role

router = APIRouter()


@router.post(
    "/users/{user_id}/access/networks/{network_id}",
    status_code=201,
    response_model=GrantNetworkAccessResponse,
)
def grant_network_access(
    user_id: int,
    network_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.admin)),
):
    # Check user exists
    existing = db.query(User).filter(User.id == user_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    # Check network exists
    existing = db.query(Network).filter(Network.id == network_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Network not found")

    # --- Store in DB ---
    db_network_access = UserNetworkAccess(
        user_id=user_id,
        network_id=network_id,
    )

    existing_access = (
        db.query(UserNetworkAccess)
        .filter_by(user_id=user_id, network_id=network_id)
        .first()
    )
    if existing_access:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has access to this network",
        )

    db.add(db_network_access)
    db.commit()

    # Return success for initial testing
    return {
        "message": "User now has access to this network",
        "user_id": user_id,
        "network_id": network_id,
    }


@router.post(
    "/users/{user_id}/access/churches/{church_id}",
    status_code=201,
    response_model=GrantChurchAccessResponse,
)
def grant_church_access(
    user_id: int,
    church_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.admin)),
):
    # Check user exists
    existing_user = db.query(User).filter(User.id == user_id).first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check church exists
    existing_church = db.query(Church).filter(Church.id == church_id).first()
    if not existing_church:
        raise HTTPException(status_code=404, detail="Church not found")

    # Check if access already granted
    existing_access = (
        db.query(UserChurchAccess)
        .filter_by(user_id=user_id, church_id=church_id)
        .first()
    )
    if existing_access:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has access to this church",
        )

    # Grant access
    db_access = UserChurchAccess(user_id=user_id, church_id=church_id)
    db.add(db_access)
    db.commit()

    return {
        "message": "User now has access to this church",
        "user_id": user_id,
        "church_id": church_id,
    }
