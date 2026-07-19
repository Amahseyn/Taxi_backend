from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.database import get_db
from app.models import Booking, Customer, Settings, Vehicle, Driver, DriverVehicle, Notification
from app.schemas import AdminStats, BookingDetailOut, SettingsOut, SettingsUpdate, BookingStatusUpdate, DriverCreate, DriverUpdate, DriverOut, DriverListOut, NotificationOut, NotificationCreate
from app.routers.dependencies import get_current_admin
import datetime

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])

@router.get("/stats", response_model=AdminStats)
def get_stats(db: Session = Depends(get_db)):
    today_str = datetime.date.today().isoformat()
    
    # Calculate revenue
    revenue_query = db.query(func.sum(Booking.price)).filter(Booking.payment_status == "paid").scalar()
    revenue = float(revenue_query) if revenue_query else 0.0
    
    # Calculate booking counts
    today_bookings = db.query(Booking).filter(Booking.travel_date == today_str).count()
    upcoming_bookings = db.query(Booking).filter(Booking.travel_date >= today_str).count()
    
    # Calculate customers
    customer_count = db.query(Customer).count()
    
    return {
        "today_bookings": today_bookings,
        "upcoming_bookings": upcoming_bookings,
        "revenue": revenue,
        "customer_count": customer_count
    }

@router.get("/bookings", response_model=List[BookingDetailOut])
def list_admin_bookings(
    search: Optional[str] = None,
    payment_status: Optional[str] = None,
    booking_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Booking)
    
    if search:
        # Search by ref or customer details
        query = query.join(Customer).filter(
            (Booking.booking_reference.ilike(f"%{search}%")) |
            (Customer.name.ilike(f"%{search}%")) |
            (Customer.email.ilike(f"%{search}%")) |
            (Customer.phone.ilike(f"%{search}%"))
        )
        
    if payment_status:
        query = query.filter(Booking.payment_status == payment_status)
        
    if booking_status:
        query = query.filter(Booking.booking_status == booking_status)
        
    bookings = query.order_by(Booking.travel_date.desc(), Booking.travel_time.desc()).all()
    
    result = []
    for b in bookings:
        result.append({
            "id": b.id,
            "booking_reference": b.booking_reference,
            "journey_type": b.journey_type,
            "pickup_address": b.pickup_address,
            "destination_address": b.destination_address,
            "price": b.price,
            "payment_status": b.payment_status,
            "booking_status": b.booking_status,
            "travel_date": b.travel_date,
            "travel_time": b.travel_time,
            "created_at": b.created_at,
            
            "customer_name": b.customer.name if b.customer else None,
            "customer_phone": b.customer.phone if b.customer else None,
            "customer_email": b.customer.email if b.customer else None,
            "vehicle_name": b.vehicle.name if b.vehicle else None,
            "passengers": b.passengers,
            "large_luggage": b.large_luggage,
            "small_luggage": b.small_luggage,
            "distance_miles": b.distance_miles,
            "duration_minutes": b.duration_minutes,
            "flight_number": b.flight_number,
            "terminal": b.terminal,
            "return_journey_data": b.return_journey_data,
            "driver_name": f"{b.driver.first_name} {b.driver.last_name}" if b.driver else None,
            "driver_vehicle_make": b.driver.vehicle.make if b.driver and b.driver.vehicle else None,
            "driver_vehicle_model": b.driver.vehicle.model if b.driver and b.driver.vehicle else None,
            "driver_vehicle_class": b.driver.vehicle.vehicle_class.name if b.driver and b.driver.vehicle and b.driver.vehicle.vehicle_class else None
        })
        
    return result

@router.patch("/bookings/{booking_id}", response_model=BookingDetailOut)
def update_booking_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    
    if payload.booking_status:
        if payload.booking_status not in ["pending", "confirmed", "completed", "cancelled"]:
            raise HTTPException(status_code=400, detail="Invalid booking status.")
        
        # State transition rules: must be confirmed before completed
        current_status = booking.booking_status
        new_status = payload.booking_status
        valid_transitions = {
            "pending": ["confirmed", "cancelled"],
            "confirmed": ["completed", "cancelled"],
            "completed": [],
            "cancelled": []
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status transition: cannot change from {current_status} to {new_status}. Must be confirmed first."
            )
        
        booking.booking_status = new_status

    if payload.payment_status:
        if payload.payment_status not in ["pending", "paid", "failed", "refunded"]:
            raise HTTPException(status_code=400, detail="Invalid payment status.")
        booking.payment_status = payload.payment_status
        
    db.commit()
    db.refresh(booking)
    
    return {
        "id": booking.id,
        "booking_reference": booking.booking_reference,
        "journey_type": booking.journey_type,
        "pickup_address": booking.pickup_address,
        "destination_address": booking.destination_address,
        "price": booking.price,
        "payment_status": booking.payment_status,
        "booking_status": booking.booking_status,
        "travel_date": booking.travel_date,
        "travel_time": booking.travel_time,
        "created_at": booking.created_at,
        "customer_name": booking.customer.name if booking.customer else None,
        "customer_phone": booking.customer.phone if booking.customer else None,
        "customer_email": booking.customer.email if booking.customer else None,
        "vehicle_name": booking.vehicle.name if booking.vehicle else None,
        "passengers": booking.passengers,
        "large_luggage": booking.large_luggage,
        "small_luggage": booking.small_luggage,
        "distance_miles": booking.distance_miles,
        "duration_minutes": booking.duration_minutes,
        "flight_number": booking.flight_number,
        "terminal": booking.terminal,
        "return_journey_data": booking.return_journey_data,
        "driver_name": f"{booking.driver.first_name} {booking.driver.last_name}" if booking.driver else None,
        "driver_vehicle_make": booking.driver.vehicle.make if booking.driver and booking.driver.vehicle else None,
        "driver_vehicle_model": booking.driver.vehicle.model if booking.driver and booking.driver.vehicle else None,
        "driver_vehicle_class": booking.driver.vehicle.vehicle_class.name if booking.driver and booking.driver.vehicle and booking.driver.vehicle.vehicle_class else None
    }

@router.get("/settings", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    app_settings = db.query(Settings).first()
    if not app_settings:
        raise HTTPException(status_code=404, detail="Settings not found.")
    return app_settings

@router.put("/settings", response_model=SettingsOut)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    app_settings = db.query(Settings).first()
    if not app_settings:
        raise HTTPException(status_code=404, detail="Settings not found.")
        
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(app_settings, k, v)
        
    db.commit()
    db.refresh(app_settings)
    return app_settings

@router.get("/drivers", response_model=List[DriverListOut])
def list_drivers(include_inactive: bool = False, db: Session = Depends(get_db)):
    query = db.query(Driver)
    if not include_inactive:
        query = query.filter(Driver.active == True)
    drivers = query.order_by(Driver.last_name.asc(), Driver.first_name.asc()).all()
    result = []
    for d in drivers:
        vehicle_data = None
        if d.vehicle:
            vc = d.vehicle.vehicle_class
            vehicle_data = {
                "make": d.vehicle.make,
                "model": d.vehicle.model,
                "class": vc.name if vc else None
            }
        result.append({
            "id": d.id,
            "name": f"{d.first_name} {d.last_name}",
            "phone": d.phone,
            "status": d.status,
            "active": d.active,
            "email": d.email,
            "notes": d.notes,
            "vehicle": vehicle_data
        })
    return result

@router.post("/drivers", response_model=DriverOut)
def create_driver(payload: DriverCreate, db: Session = Depends(get_db)):
    driver = Driver(
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        email=payload.email,
        status=payload.status,
        notes=payload.notes,
        active=payload.active
    )
    db.add(driver)
    db.flush()

    if payload.vehicle:
        vehicle_code_mapping = {}
        for vc in db.query(Vehicle).all():
            vehicle_code_mapping[vc.code] = vc.id
        
        vcid = payload.vehicle.vehicle_class_id
        actual_vcid = vehicle_code_mapping.get(vcid, vcid) if isinstance(vcid, str) else vcid
        vehicle_class = db.query(Vehicle).filter(Vehicle.id == actual_vcid).first()
        if not vehicle_class:
            db.rollback()
            raise HTTPException(status_code=400, detail="Invalid vehicle class.")
        
        driver_vehicle = DriverVehicle(
            driver_id=driver.id,
            vehicle_class_id=actual_vcid,
            registration_number=payload.vehicle.registration_number,
            make=payload.vehicle.make,
            model=payload.vehicle.model,
            year=payload.vehicle.year,
            colour=payload.vehicle.colour,
            seats=payload.vehicle.seats
        )
        db.add(driver_vehicle)

    db.commit()
    db.refresh(driver)
    if driver.vehicle:
        vc = driver.vehicle.vehicle_class
        driver.vehicle.vehicle_class_name = vc.name if vc else None
        driver.vehicle.vehicle_class_code = vc.code if vc else None
    return driver

@router.get("/drivers/{driver_id}", response_model=DriverOut)
def get_driver(driver_id: int, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found.")
    if driver.vehicle:
        vc = driver.vehicle.vehicle_class
        driver.vehicle.vehicle_class_name = vc.name if vc else None
        driver.vehicle.vehicle_class_code = vc.code if vc else None
    return driver

@router.put("/drivers/{driver_id}", response_model=DriverOut)
def update_driver(driver_id: int, payload: DriverUpdate, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found.")

    for k, v in payload.model_dump(exclude_unset=True).items():
        if k == "vehicle" and v is not None:
            if driver.vehicle is None:
                driver.vehicle = DriverVehicle(driver_id=driver.id)
            
            vehicle_code_mapping = {}
            for vc in db.query(Vehicle).all():
                vehicle_code_mapping[vc.code] = vc.id
            
            for vk, vv in v.model_dump(exclude_unset=True).items():
                if vk == "vehicle_class_id":
                    vid = vehicle_code_mapping.get(vv, vv) if isinstance(vv, str) else vv
                    vehicle_class = db.query(Vehicle).filter(Vehicle.id == vid).first()
                    if not vehicle_class:
                        raise HTTPException(status_code=400, detail="Invalid vehicle class.")
                    vv = vid
                setattr(driver.vehicle, vk, vv)
        else:
            setattr(driver, k, v)

    db.commit()
    db.refresh(driver)
    if driver.vehicle:
        vc = driver.vehicle.vehicle_class
        driver.vehicle.vehicle_class_name = vc.name if vc else None
        driver.vehicle.vehicle_class_code = vc.code if vc else None
    return driver

@router.delete("/drivers/{driver_id}")
def deactivate_driver(driver_id: int, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found.")
    driver.active = False
    driver.status = "inactive"
    db.commit()
    return {"message": "Driver deactivated successfully."}

@router.patch("/bookings/{booking_id}/assign-driver")
def assign_driver_to_booking(booking_id: int, driver_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    
    driver = db.query(Driver).filter(Driver.id == driver_id, Driver.active == True).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found or inactive.")
    
    booking.driver_id = driver.id
    booking.booking_status = "confirmed"
    driver.status = "busy"
    db.commit()
    db.refresh(booking)
    
    # Create notification for driver
    notification = Notification(
        title="New Task Assigned",
        message=f"You have been assigned a new booking. Ref: {booking.booking_reference}. Pickup: {booking.pickup_address} at {booking.travel_date} {booking.travel_time}.",
        type="task_assigned",
        driver_id=driver.id,
        booking_id=booking.id
    )
    db.add(notification)
    db.commit()
    
    return {
        "id": booking.id,
        "driver_id": driver.id,
        "driver_name": f"{driver.first_name} {driver.last_name}",
        "vehicle_make": driver.vehicle.make if driver.vehicle else None,
        "vehicle_model": driver.vehicle.model if driver.vehicle else None,
        "vehicle_class": driver.vehicle.vehicle_class.name if driver.vehicle and driver.vehicle.vehicle_class else None
    }

@router.get("/notifications", response_model=List[NotificationOut])
def list_notifications(db: Session = Depends(get_db)):
    notifications = db.query(Notification).order_by(Notification.created_at.desc()).limit(50).all()
    return notifications

@router.post("/notifications", response_model=NotificationOut)
def create_notification(payload: NotificationCreate, db: Session = Depends(get_db)):
    notification = Notification(
        title=payload.title,
        message=payload.message,
        type=payload.type,
        booking_id=payload.booking_id,
        driver_id=payload.driver_id
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification

@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notification.read = True
    db.commit()
    return {"status": "success"}
