import pytest
import datetime
import zoneinfo
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import PricingRule, Vehicle, Settings
from app.services.pricing_service import PricingService, parse_travel_datetime, get_business_local_time

# In-memory database setup for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Add seed data
    settings = Settings(
        business_name="Test Colchester Taxi",
        minimum_booking_notice_hours=3,
        cancellation_window_hours=24
    )
    db.add(settings)
    
    vehicles = [
        Vehicle(name="Saloon", code="saloon", max_passengers=4, large_luggage_capacity=2, small_luggage_capacity=2, active=True),
        Vehicle(name="Minibus", code="minibus", max_passengers=8, large_luggage_capacity=8, small_luggage_capacity=8, active=True),
    ]
    for v in vehicles:
        db.add(v)
        
    airport_rule = PricingRule(
        type="airport",
        airport_code="STN",
        vehicle_prices={"saloon": 75.0, "minibus": 120.0},
        active=True
    )
    db.add(airport_rule)
    
    local_rule = PricingRule(
        type="local",
        minimum_fare=15.0,
        per_mile_rate=2.5,
        vehicle_prices={"saloon": 1.0, "minibus": 1.8},
        active=True
    )
    db.add(local_rule)
    
    db.commit()
    
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_booking_notice_validation(db_session):
    now_london = get_business_local_time("Europe/London")
    
    # 1. Booking for 5 hours in future should be allowed
    future_time = now_london + datetime.timedelta(hours=5)
    date_str = future_time.strftime("%Y-%m-%d")
    time_str = future_time.strftime("%H:%M")
    
    allowed, reason = PricingService.check_booking_notice(date_str, time_str, db_session)
    assert allowed is True
    
    # 2. Booking for 1 hour in future should be blocked
    near_time = now_london + datetime.timedelta(hours=1)
    date_str_near = near_time.strftime("%Y-%m-%d")
    time_str_near = near_time.strftime("%H:%M")
    
    allowed, reason = PricingService.check_booking_notice(date_str_near, time_str_near, db_session)
    assert allowed is False
    assert "Please call the office" in reason

def test_airport_quote_calculation(db_session):
    # Calculate quote for Stansted (fixed price 75 for Saloon)
    quote = PricingService.calculate_quote(
        db=db_session,
        journey_type="Airport Drop-off",
        pickup_lat=51.896,
        pickup_lng=0.892,
        dest_lat=51.885,
        dest_lng=0.235,
        vehicle_code="saloon",
        airport_code="STN"
    )
    
    assert quote["price"] == 75.0
    assert quote["vehicle_code"] == "saloon"
    assert "Airport" in quote["rule_used"]

def test_local_quote_calculation(db_session):
    # Calculate quote for local trip (not matching any airport)
    # Distance will fallback to straight-line rough calculation or be computed
    # Minimum fare = 15.0, per mile = 2.5. Saloon multiplier = 1.0.
    quote = PricingService.calculate_quote(
        db=db_session,
        journey_type="Local Journey",
        pickup_lat=51.896,
        pickup_lng=0.892,
        dest_lat=51.920,
        dest_lng=0.910,
        vehicle_code="saloon",
        airport_code=None
    )
    
    # Pricing is based on distance. Let's make sure the price is at least minimum fare
    assert quote["price"] >= 15.0
    assert "Local" in quote["rule_used"]
