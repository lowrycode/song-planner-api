from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import (
    User,
    UserRole,
    Network,
    Church,
    ChurchActivity,
    UserNetworkAccess,
    UserChurchAccess,
    UserChurchActivityAccess,
)
from app.schemas.users import (
    GrantNetworkAccessResponse,
    GrantChurchAccessResponse,
    GrantChurchActivityAccessResponse,
    UserAccountResponse,
    UserUpdateRequest,
    AdminUserUpdateRequest,
    NetworkAccess,
    ChurchActivityAccess,
)
from app.dependencies import require_min_role

router = APIRouter()


@router.get(
    "/{user_id}/access/networks",
    response_model=list[NetworkAccess],
    status_code=status.HTTP_200_OK,
)
def get_network_access_for_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_min_role(UserRole.normal)),
):
    """
    Get a list of networks that the specified user has access to.

    Args:
        user_id (int): The ID of the user whose network access is requested.
        db (Session): The database session.
        current_user (User): The authenticated user making the request.

    Raises:
        HTTPException:
            - 404 if the user does not exist.
            - 403 if the current user is not allowed to view the requested user's access.

    Returns:
        List of networks the user has access to.
    """
    # Check user exists
    user = (
        db.query(User)
        .options(
            joinedload(User.network_accesses).joinedload(
                UserNetworkAccess.network
            )
        )
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Allow if current_user is the same user or admin in same network
    if current_user.id != user_id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    if (
        current_user.role == UserRole.admin
        and current_user.network_id != user.network_id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Return list of networks user has access to
    return [
        NetworkAccess(
            id=access.network.id,
            network_id=access.network.id,
            network_name=access.network.name,
            network_slug=access.network.slug,
        )
        for access in user.network_accesses
    ]


@router.post(
    "/{user_id}/access/networks/{network_id}",
    status_code=status.HTTP_201_CREATED,
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


@router.delete(
    "/{user_id}/access/networks/{network_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_network_access(
    user_id: int,
    network_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.admin)),
):
    access = (
        db.query(UserNetworkAccess)
        .filter_by(user_id=user_id, network_id=network_id)
        .first()
    )

    if not access:
        raise HTTPException(status_code=404, detail="Access not found")

    db.delete(access)
    db.commit()


@router.post(
    "/{user_id}/access/churches/{church_id}",
    status_code=status.HTTP_201_CREATED,
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


@router.delete(
    "/{user_id}/access/churches/{church_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_church_access(
    user_id: int,
    church_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.admin)),
):
    access = (
        db.query(UserChurchAccess)
        .filter_by(user_id=user_id, church_id=church_id)
        .first()
    )

    if not access:
        raise HTTPException(status_code=404, detail="Access not found")

    db.delete(access)
    db.commit()


@router.get(
    "/{user_id}/access/activities",
    response_model=list[ChurchActivityAccess],
    status_code=status.HTTP_200_OK,
)
def get_church_activity_access_for_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_min_role(UserRole.normal)),
):
    """
    Get a list of church activities that the specified user has access to.

    Args:
        user_id (int): The ID of the user whose church activity access is requested.
        db (Session): The database session.
        current_user (User): The authenticated user making the request.

    Raises:
        HTTPException:
            - 404 if the user does not exist.
            - 403 if the current user is not allowed to view the requested
            user's access.

    Returns:
        List of church activities the user has access to.
    """
    # Check user exists
    user = (
        db.query(User)
        .options(
            joinedload(User.activity_accesses).joinedload(
                UserChurchActivityAccess.church_activity
            )
        )
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Allow if current_user is the same user or admin in same network
    if current_user.id != user_id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    if (
        current_user.role == UserRole.admin
        and current_user.network_id != user.network_id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Query activities that user has access to
    return [
        ChurchActivityAccess(
            id=access.church_activity.id,
            church_activity_id=access.church_activity.id,
            church_activity_name=access.church_activity.name,
            church_activity_slug=access.church_activity.slug,
        )
        for access in user.activity_accesses
    ]


@router.post(
    "/{user_id}/access/activities/{activity_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=GrantChurchActivityAccessResponse,
)
def grant_church_activity_access(
    user_id: int,
    activity_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.admin)),
):
    # Check user exists
    existing_user = db.query(User).filter(User.id == user_id).first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check church activity exists
    existing_activity = (
        db.query(ChurchActivity).filter(ChurchActivity.id == activity_id).first()
    )
    if not existing_activity:
        raise HTTPException(status_code=404, detail="Church activity not found")

    # Check if access already granted
    existing_access = (
        db.query(UserChurchActivityAccess)
        .filter_by(user_id=user_id, church_activity_id=activity_id)
        .first()
    )
    if existing_access:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has access to this church activity",
        )

    # Grant access
    db_access = UserChurchActivityAccess(
        user_id=user_id, church_activity_id=activity_id
    )
    db.add(db_access)
    db.commit()

    return {
        "message": "User now has access to this church activity",
        "user_id": user_id,
        "activity_id": activity_id,
    }


@router.delete(
    "/{user_id}/access/activities/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_church_activity_access(
    user_id: int,
    activity_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.admin)),
):
    access = (
        db.query(UserChurchActivityAccess)
        .filter_by(user_id=user_id, church_activity_id=activity_id)
        .first()
    )

    if not access:
        raise HTTPException(status_code=404, detail="Access not found")

    db.delete(access)
    db.commit()


@router.get("/{user_id}", response_model=UserAccountResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_min_role(UserRole.normal)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    if current_user.id != user_id and current_user.role != UserRole.admin:
        raise HTTPException(403, "Forbidden")

    if (
        current_user.role == UserRole.admin
        and current_user.network_id != user.network_id
    ):
        raise HTTPException(403, "Forbidden")

    return user


@router.put("/{user_id}", response_model=UserAccountResponse)
def update_user(
    user_id: int,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_min_role(UserRole.normal)),
):
    """
    Update user account details.

    This endpoint allows a user to update their own account details, or an admin
    to update details for a user within the same network.

    Regular users can update username, first name and last name.
    Only admins can update the user's role, network and church.

    Args:
        user_id (int): The ID of the user whose details are being updated.
        body (dict): The request body containing the updated user information.
        db (Session): The database session for querying and committing changes.
        current_user (User): The currently authenticated user performing the update.

    Raises:
        HTTPException:
            - 404 if the user to update does not exist.
            - 403 if the current user does not have permission to update the user.
            - 400 if the provided username is already taken by another user.

    Returns:
        UserAccountResponse: The updated user details.

    """
    # Apply correct schema
    if current_user.role == UserRole.admin:
        data = AdminUserUpdateRequest(**body)
    else:
        data = UserUpdateRequest(**body)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    if current_user.id != user_id and current_user.role != UserRole.admin:
        raise HTTPException(403, "Forbidden")

    if (
        current_user.role == UserRole.admin
        and current_user.network_id != user.network_id
    ):
        raise HTTPException(403, "Forbidden")

    # Check username is not already taken by ANOTHER user
    existing_user = (
        db.query(User)
        .filter(User.username == data.username, User.id != user_id)
        .first()
    )
    if existing_user:
        raise HTTPException(400, "Username already taken")

    # Update fields
    user.username = data.username
    user.first_name = data.first_name
    user.last_name = data.last_name

    # Only allow admin to update role, network or church
    if current_user.role == UserRole.admin:
        user.role = data.role
        user.network_id = data.network_id
        user.church_id = data.church_id

    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_min_role(UserRole.normal)),
):
    """
    Delete a user account.

    This endpoint allows a user to delete their own account, or an admin
    to delete a user within the same network.

    Regular users may only delete themselves.
    Admin users may delete users belonging to their own network.

    Args:
        user_id (int): The ID of the user to delete.
        db (Session): The database session.
        current_user (User): The authenticated user performing the deletion.

    Raises:
        HTTPException:
            - 404 if the user does not exist.
            - 403 if the current user is not authorized to delete the user.

    Returns:
        None
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Regular users can only delete themselves
    if current_user.id != user_id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Admins may only delete users in their own network
    if (
        current_user.role == UserRole.admin
        and current_user.network_id != user.network_id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    db.delete(user)
    db.commit()
