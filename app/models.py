import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="customer") # "admin" or "customer"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    customer = relationship("Customer", uselist=False, back_populates="user", cascade="all, delete-orphan")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    total_bookings = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="customer")
    bookings = relationship("Booking", back_populates="customer")

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True, nullable=False) # "saloon", "estate", "executive", "minibus"
    max_passengers = Column(Integer, nullable=False)
    large_luggage_capacity = Column(Integer, nullable=False)
    small_luggage_capacity = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)

    bookings = relationship("Booking", back_populates="vehicle")

class Airport(Base):
    __tablename__ = "airports"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False) # "STN", "LHR", "LGW", etc.
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    active = Column(Boolean, default=True)

class PricingRule(Base):
    __tablename__ = "pricing_rules"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False) # "airport", "local", "mileage"
    airport_code = Column(String, nullable=True)
    vehicle_prices = Column(JSON, nullable=True) # {"saloon": 75, "estate": 85, "executive": 90, "minibus": 120}
    minimum_fare = Column(Float, nullable=True)
    per_mile_rate = Column(Float, nullable=True)
    active = Column(Boolean, default=True)

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_reference = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    journey_type = Column(String, nullable=False) # "Airport Pickup", "Airport Drop-off", "Return Journey", "Local Journey", "Long Distance"
    
    pickup_address = Column(String, nullable=False)
    pickup_postcode = Column(String, nullable=True)
    pickup_lat = Column(Float, nullable=False)
    pickup_lng = Column(Float, nullable=False)
    
    destination_address = Column(String, nullable=False)
    destination_postcode = Column(String, nullable=True)
    destination_lat = Column(Float, nullable=False)
    destination_lng = Column(Float, nullable=False)
    
    airport_code = Column(String, nullable=True)
    terminal = Column(String, nullable=True)
    flight_number = Column(String, nullable=True)
    
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    passengers = Column(Integer, default=1)
    large_luggage = Column(Integer, default=0)
    small_luggage = Column(Integer, default=0)
    
    distance_miles = Column(Float, nullable=False)
    duration_minutes = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    payment_method = Column(String, default="stripe")
    payment_status = Column(String, default="pending") # "pending", "paid", "failed", "refunded"
    booking_status = Column(String, default="pending") # "pending", "confirmed", "completed", "cancelled"
    
    travel_date = Column(String, nullable=False, index=True) # "YYYY-MM-DD"
    travel_time = Column(String, nullable=False) # "HH:MM"
    
    return_journey_data = Column(JSON, nullable=True) # return date/time/flight info
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="bookings")
    vehicle = relationship("Vehicle", back_populates="bookings")
    driver = relationship("Driver", back_populates="bookings")
    payments = relationship("Payment", back_populates="booking")

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=True)
    status = Column(String, default="inactive") # "available", "busy", "inactive"
    active = Column(Boolean, default=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    vehicle = relationship("DriverVehicle", uselist=False, back_populates="driver", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="driver")

class DriverVehicle(Base):
    __tablename__ = "driver_vehicles"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), unique=True, nullable=False)
    vehicle_class_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    registration_number = Column(String, unique=True, nullable=False)
    make = Column(String, nullable=False)
    model = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    colour = Column(String, nullable=True)
    seats = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    driver = relationship("Driver", back_populates="vehicle")
    vehicle_class = relationship("Vehicle", foreign_keys=[vehicle_class_id])

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    amount = Column(Float, nullable=False)
    stripe_session_id = Column(String, nullable=True)
    stripe_payment_intent_id = Column(String, nullable=True)
    status = Column(String, nullable=False) # "pending", "paid", "failed", "refunded"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    booking = relationship("Booking", back_populates="payments")

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String, default="Colchester Airport Taxi")
    phone = Column(String, default="+44 1206 555555")
    email = Column(String, default="bookings@colchesterairporttaxi.co.uk")
    minimum_booking_notice_hours = Column(Integer, default=3)
    cancellation_window_hours = Column(Integer, default=24)
    stripe_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=True)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    type = Column(String, default="info")
    read = Column(Boolean, default=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    booking = relationship("Booking")
    driver = relationship("Driver")
