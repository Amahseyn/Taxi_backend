from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Vehicle, Airport
from app.schemas import VehicleOut, AirportOut

router = APIRouter(tags=["vehicles"])

@router.get("/vehicles", response_model=List[VehicleOut])
def list_vehicles(db: Session = Depends(get_db)):
    return db.query(Vehicle).filter(Vehicle.active == True).all()

@router.get("/airports", response_model=List[AirportOut])
def list_airports(db: Session = Depends(get_db)):
    return db.query(Airport).filter(Airport.active == True).all()
