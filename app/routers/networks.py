from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import (
    Network,
    Church,
    User,
    UserRole,
    UserNetworkAccess,
    UserChurchAccess,
    UserChurchActivityAccess,
)
from app.schemas.networks import NetworkSchema, ChurchSchema
from app.schemas.users import (
    UserWithAccessesResponse,
    NetworkAccess,
    ChurchAccess,
    ChurchActivityAccess,
)
from app.dependencies import require_min_role

router = APIRouter()


@router.get("/", response_model=list[NetworkSchema])
def list_networks(db: Session = Depends(get_db)):
    return db.query(Network).order_by(Network.name.asc()).all()


@router.get("/{network_id}/churches", response_model=list[ChurchSchema])
def list_churches_by_network(network_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Church)
        .filter(Church.network_id == network_id)
        .order_by(Church.name.asc())
        .all()
    )


@router.get(
    "/{network_id}/users",
    response_model=list[UserWithAccessesResponse],
    status_code=status.HTTP_200_OK,
)
def list_users_with_accesses(
    network_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_min_role(UserRole.admin)),
):
    """
    Get all users in a network along with all their access
    (networks, churches, church activities).

    Admin-only endpoint.

    Args:
        network_id (int): Network ID.
        db (Session): Database session.
        current_user (User): Authenticated admin.

    Raises:
        HTTPException:
            - 404 if network does not exist
            - 403 if admin is not in the requested network

    Returns:
        List of users with full access details.
    """

    # Check network exists
    network = db.query(Network).filter(Network.id == network_id).first()
    if not network:
        raise HTTPException(status_code=404, detail="Network not found")

    # Admin must belong to the same network
    if current_user.network_id != network_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    users = (
        db.query(User)
        .options(
            joinedload(User.network_accesses).joinedload(UserNetworkAccess.network),
            joinedload(User.church_accesses).joinedload(UserChurchAccess.church),
            joinedload(User.activity_accesses).joinedload(
                UserChurchActivityAccess.church_activity
            ),
        )
        .filter(User.network_id == network_id)
        .all()
    )

    return [
        UserWithAccessesResponse(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            network=user.network,
            church=user.church,
            accesses={
                "networks": [
                    NetworkAccess(
                        id=access.network.id,
                        network_id=access.network.id,
                        network_name=access.network.name,
                        network_slug=access.network.slug,
                    )
                    for access in user.network_accesses
                ],
                "churches": [
                    ChurchAccess(
                        id=access.church.id,
                        church_id=access.church.id,
                        church_name=access.church.name,
                        church_slug=access.church.slug,
                    )
                    for access in user.church_accesses
                ],
                "church_activities": [
                    ChurchActivityAccess(
                        id=access.church_activity.id,
                        church_activity_id=access.church_activity.id,
                        church_activity_name=access.church_activity.name,
                        church_activity_slug=access.church_activity.slug,
                    )
                    for access in user.activity_accesses
                ]}
        )
        for user in users
    ]
