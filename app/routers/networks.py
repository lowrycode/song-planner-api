from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Network, Church
from app.schemas.networks import NetworkSchema, ChurchSchema

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
