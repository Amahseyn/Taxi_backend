from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any

# Authentication
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str
    phone: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str

# Vehicles & Airports
class VehicleOut(BaseModel):
    id: int
    name: str
    code: str
    max_passengers: int
    large_luggage_capacity: int
    small_luggage_capacity: int

    class Config:
        from_attributes = True

class AirportOut(BaseModel):
    id: int
    code: str
    name: str
    city: str

    class Config:
        from_attributes = True

# Pricing Engine / Quotes
class QuoteRequest(BaseModel):
    journey_type: str
    pickup_address: str
    pickup_lat: float = Field(..., ge=-90.0, le=90.0)
    pickup_lng: float = Field(..., ge=-180.0, le=180.0)
    destination_address: str
    destination_lat: float = Field(..., ge=-90.0, le=90.0)
    destination_lng: float = Field(..., ge=-180.0, le=180.0)
    vehicle_code: str
    airport_code: Optional[str] = None
    travel_date: str # YYYY-MM-DD
    travel_time: str # HH:MM

class QuoteResponse(BaseModel):
    distance_miles: float
    duration_minutes: float
    price: float
    vehicle_code: str
    notice_allowed: bool
    notice_reason: str

# Bookings
class ReturnJourneyData(BaseModel):
    return_date: str
    return_time: str
    return_flight_number: Optional[str] = None

class BookingCreate(BaseModel):
    journey_type: str
    pickup_address: str
    pickup_postcode: Optional[str] = None
    pickup_lat: float
    pickup_lng: float
    destination_address: str
    destination_postcode: Optional[str] = None
    destination_lat: float
    destination_lng: float
    airport_code: Optional[str] = None
    terminal: Optional[str] = None
    flight_number: Optional[str] = None
    vehicle_code: str
    passengers: int = 1
    large_luggage: int = 0
    small_luggage: int = 0
    travel_date: str
    travel_time: str
    return_journey_data: Optional[ReturnJourneyData] = None
    
    # Customer Info (for guest checkout or registration fallback)
    name: str
    email: EmailStr
    phone: str

class BookingOut(BaseModel):
    id: int
    booking_reference: str
    journey_type: str
    pickup_address: str
    destination_address: str
    price: float
    payment_status: str
    booking_status: str
    travel_date: str
    travel_time: str
    created_at: Any

    class Config:
        from_attributes = True

class BookingDetailOut(BookingOut):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    vehicle_name: Optional[str] = None
    passengers: int
    large_luggage: int
    small_luggage: int
    distance_miles: float
    duration_minutes: float
    flight_number: Optional[str] = None
    terminal: Optional[str] = None
    return_journey_data: Optional[Dict[str, Any]] = None
    driver_name: Optional[str] = None
    driver_vehicle_make: Optional[str] = None
    driver_vehicle_model: Optional[str] = None
    driver_vehicle_class: Optional[str] = None

# Admin Dashboard Stats
class AdminStats(BaseModel):
    today_bookings: int
    upcoming_bookings: int
    revenue: float
    customer_count: int

# Operational Settings
class SettingsOut(BaseModel):
    business_name: str
    phone: str
    email: str
    minimum_booking_notice_hours: int
    cancellation_window_hours: int
    stripe_enabled: bool
    sms_enabled: bool

class SettingsUpdate(BaseModel):
    business_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    minimum_booking_notice_hours: Optional[int] = None
    cancellation_window_hours: Optional[int] = None
    stripe_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None

class BookingStatusUpdate(BaseModel):
    booking_status: Optional[str] = None
    payment_status: Optional[str] = None

# Drivers
class DriverVehicleBase(BaseModel):
    vehicle_class_id: int
    registration_number: str
    make: str
    model: str
    year: Optional[int] = None
    colour: Optional[str] = None
    seats: Optional[int] = None

class DriverVehicleCreate(DriverVehicleBase):
    pass

class DriverVehicleUpdate(DriverVehicleBase):
    vehicle_class_id: Optional[int] = None
    registration_number: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None

class DriverVehicleOut(BaseModel):
    id: int
    vehicle_class_id: int
    registration_number: str
    make: str
    model: str
    year: Optional[int] = None
    colour: Optional[str] = None
    seats: Optional[int] = None
    vehicle_class_name: Optional[str] = None
    vehicle_class_code: Optional[str] = None

    class Config:
        from_attributes = True

class DriverBase(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    status: str = "inactive"
    notes: Optional[str] = None
    active: bool = True
    vehicle: Optional[DriverVehicleCreate] = None

class DriverCreate(DriverBase):
    pass

class DriverUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None
    vehicle: Optional[DriverVehicleUpdate] = None

class DriverOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    status: str
    active: bool
    notes: Optional[str] = None
    vehicle: Optional[DriverVehicleOut] = None

    class Config:
        from_attributes = True

class DriverListOut(BaseModel):
    id: int
    name: str
    phone: str
    status: str
    active: bool
    email: Optional[str] = None
    notes: Optional[str] = None
    vehicle: Optional[dict] = None

    class Config:
        from_attributes = True

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    type: str
    read: bool
    booking_id: Optional[int] = None
    driver_id: Optional[int] = None
    created_at: Any

    class Config:
        from_attributes = True

class NotificationCreate(BaseModel):
    title: str
    message: str
    type: str = "info"
    booking_id: Optional[int] = None
    driver_id: Optional[int] = None
