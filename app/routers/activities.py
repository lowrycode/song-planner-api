from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    UserRole,
    User,
    ChurchActivity,
)
from app.schemas.activities import (
    ChurchActivitySchema,
)
from app.dependencies import require_min_role


router = APIRouter()


@router.get("/", status_code=200, response_model=list[ChurchActivitySchema])
def list_viewable_church_activities(
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
):
    # Todo: replace with user-permissions approach
    viewable_activity_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    query = (
        db.query(ChurchActivity)
        .filter(ChurchActivity.id.in_(viewable_activity_ids))
        .order_by(ChurchActivity.name.asc())
    )
    return query.all()
