import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, get_db
from app.main import app
from app.models import User, Customer, Vehicle, Airport, PricingRule, Settings, Driver, DriverVehicle
from app.core.auth import get_password_hash
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Isolated in-memory database for the whole test session
# ---------------------------------------------------------------------------
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_data(db):
    """Insert vehicles, airports, pricing rules, settings and sample users."""
    db.add(Settings(
        business_name="Test Colchester Taxi",
        phone="+44 1206 555555",
        email="bookings@test.co.uk",
        minimum_booking_notice_hours=3,
        cancellation_window_hours=24,
        stripe_enabled=False,
        sms_enabled=False,
    ))

    for v in [
        Vehicle(name="Saloon", code="saloon", max_passengers=4, large_luggage_capacity=2, small_luggage_capacity=2, active=True),
        Vehicle(name="Estate", code="estate", max_passengers=4, large_luggage_capacity=3, small_luggage_capacity=3, active=True),
        Vehicle(name="Executive", code="executive", max_passengers=4, large_luggage_capacity=2, small_luggage_capacity=2, active=True),
        Vehicle(name="Minibus", code="minibus", max_passengers=8, large_luggage_capacity=8, small_luggage_capacity=8, active=True),
    ]:
        db.add(v)

    for code, name in [("STN", "Stansted"), ("LHR", "Heathrow"), ("LGW", "Gatwick")]:
        db.add(Airport(code=code, name=name, city="London", active=True))

    db.add(PricingRule(
        type="airport", airport_code="STN",
        vehicle_prices={"saloon": 75.0, "estate": 85.0, "executive": 90.0, "minibus": 120.0},
        active=True,
    ))
    db.add(PricingRule(
        type="local", minimum_fare=15.0, per_mile_rate=2.5,
        vehicle_prices={"saloon": 1.0, "estate": 1.2, "executive": 1.4, "minibus": 1.8},
        active=True,
    ))

    # Sample admin
    admin = User(email="admin@admin.com", password_hash=get_password_hash("admin"), role="admin")
    db.add(admin)
    db.flush()
    db.add(Customer(user_id=admin.id, name="Admin User", email="admin@admin.com", phone="+44 1206 000000"))

    # Sample customer
    cust = User(email="customer@example.com", password_hash=get_password_hash("secret123"), role="customer")
    db.add(cust)
    db.flush()
    db.add(Customer(user_id=cust.id, name="Sample Customer", email="customer@example.com", phone="+44 1206 111111"))

    # Sample driver
    driver = Driver(first_name="Ahmed", last_name="Ali", phone="07123456789", email="ahmed@test.com", status="available", active=True)
    db.add(driver)
    db.flush()
    db.add(DriverVehicle(
        driver_id=driver.id,
        vehicle_class_id=1,
        registration_number="AB12CDE",
        make="Mercedes",
        model="E-Class",
        year=2024,
        colour="Black",
        seats=4
    ))

    db.commit()


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_data(db)
    db.close()

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def register_payload(email="newuser@example.com", password="password123", name="New User", phone="+44 1206 222222"):
    return {"email": email, "password": password, "name": name, "phone": phone}


def make_future_booking_date():
    import datetime
    import zoneinfo
    now = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/London")) + datetime.timedelta(days=2)
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M")


def auth_header(client, email, password):
    r = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def test_health_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "up and running" in r.json()["message"]


def test_register_new_user(client):
    r = client.post("/api/v1/auth/register", json=register_payload())
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "newuser@example.com"
    assert body["role"] == "customer"
    assert "password" not in body


def test_register_duplicate_email(client):
    client.post("/api/v1/auth/register", json=register_payload(email="customer@example.com"))
    r = client.post("/api/v1/auth/register", json=register_payload(email="customer@example.com"))
    assert r.status_code == 400


def test_login_success(client):
    r = client.post("/api/v1/auth/login", data={"username": "customer@example.com", "password": "secret123"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["role"] == "customer"


def test_login_wrong_password(client):
    r = client.post("/api/v1/auth/login", data={"username": "customer@example.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_with_token(client):
    h = auth_header(client, "customer@example.com", "secret123")
    r = client.get("/api/v1/auth/me", headers=h)
    assert r.status_code == 200
    assert r.json()["email"] == "customer@example.com"


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------
def quote_payload(**overrides):
    d, t = make_future_booking_date()
    base = {
        "journey_type": "Airport Drop-off",
        "pickup_address": "Colchester",
        "pickup_lat": 51.896, "pickup_lng": 0.892,
        "destination_address": "Stansted Airport",
        "destination_lat": 51.885, "destination_lng": 0.235,
        "vehicle_code": "saloon",
        "airport_code": "STN",
        "travel_date": d, "travel_time": t,
    }
    base.update(overrides)
    return base


def test_quote_airport_fixed_price(client):
    r = client.post("/api/v1/bookings/quote", json=quote_payload())
    assert r.status_code == 200
    body = r.json()
    assert body["price"] == 75.0
    assert body["vehicle_code"] == "saloon"
    assert body["notice_allowed"] is True


def test_quote_minibus_higher_than_saloon(client):
    saloon = client.post("/api/v1/bookings/quote", json=quote_payload(vehicle_code="saloon")).json()
    minibus = client.post("/api/v1/bookings/quote", json=quote_payload(vehicle_code="minibus")).json()
    assert minibus["price"] > saloon["price"]


def test_quote_respects_notice_window(client):
    import datetime, zoneinfo
    near = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/London")) + datetime.timedelta(hours=1)
    r = client.post("/api/v1/bookings/quote", json=quote_payload(
        travel_date=near.strftime("%Y-%m-%d"), travel_time=near.strftime("%H:%M")))
    assert r.status_code == 200
    assert r.json()["notice_allowed"] is False


def test_quote_local_journey_min_fare(client):
    r = client.post("/api/v1/bookings/quote", json=quote_payload(
        journey_type="Local Journey", airport_code=None,
        destination_lat=51.920, destination_lng=0.910))
    assert r.status_code == 200
    # Local price uses min fare + per-mile; should be >= minimum fare
    assert r.json()["price"] >= 15.0


# ---------------------------------------------------------------------------
# Bookings (create, list, cancel, webhook)
# ---------------------------------------------------------------------------
def booking_payload(**overrides):
    d, t = make_future_booking_date()
    base = {
        "journey_type": "Airport Drop-off",
        "pickup_address": "12 High Street, Colchester",
        "pickup_postcode": "CO1 1AA",
        "pickup_lat": 51.896, "pickup_lng": 0.892,
        "destination_address": "Stansted Airport",
        "destination_postcode": "CM24 1QW",
        "destination_lat": 51.885, "destination_lng": 0.235,
        "airport_code": "STN",
        "vehicle_code": "saloon",
        "passengers": 2,
        "large_luggage": 1,
        "small_luggage": 1,
        "travel_date": d, "travel_time": t,
        "name": "Sample Customer",
        "email": "customer@example.com",
        "phone": "+44 1206 111111",
    }
    base.update(overrides)
    return base


def test_create_booking_as_guest(client):
    r = client.post("/api/v1/bookings/create", json=booking_payload())
    assert r.status_code == 200
    body = r.json()
    assert body["booking_reference"].startswith("TX-")
    assert "stripe_session_url" in body


def test_create_booking_as_logged_in_customer(client):
    h = auth_header(client, "customer@example.com", "secret123")
    r = client.post("/api/v1/bookings/create", json=booking_payload(), headers=h)
    assert r.status_code == 200


def test_create_booking_rejects_short_notice(client):
    import datetime, zoneinfo
    near = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/London")) + datetime.timedelta(hours=1)
    r = client.post("/api/v1/bookings/create", json=booking_payload(
        travel_date=near.strftime("%Y-%m-%d"), travel_time=near.strftime("%H:%M")))
    assert r.status_code == 400


def test_my_bookings_returns_user_bookings(client):
    h = auth_header(client, "customer@example.com", "secret123")
    client.post("/api/v1/bookings/create", json=booking_payload(), headers=h)
    r = client.get("/api/v1/bookings/my-bookings", headers=h)
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert r.json()[0]["booking_reference"].startswith("TX-")


def test_my_bookings_requires_auth(client):
    assert client.get("/api/v1/bookings/my-bookings").status_code == 401


def test_webhook_marks_booking_paid(client):
    created = client.post("/api/v1/bookings/create", json=booking_payload()).json()
    ref = created["booking_reference"]
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"booking_reference": ref}, "payment_intent": "pi_123"}},
    }
    r = client.post("/api/v1/bookings/webhook", json=event,
                    headers={"stripe-signature": "whsec_test"})
    assert r.status_code == 200
    # The booking should now be paid/confirmed (verify via admin list)
    admin_h = auth_header(client, "admin@admin.com", "admin")
    bookings = client.get("/api/v1/admin/bookings", headers=admin_h).json()
    match = next((b for b in bookings if b["booking_reference"] == ref), None)
    assert match is not None
    assert match["payment_status"] == "paid"
    assert match["booking_status"] == "confirmed"


def test_cancel_booking_success(client):
    h = auth_header(client, "customer@example.com", "secret123")
    created = client.post("/api/v1/bookings/create", json=booking_payload(), headers=h).json()
    # find booking id
    mine = client.get("/api/v1/bookings/my-bookings", headers=h).json()
    bid = mine[0]["id"]
    r = client.post(f"/api/v1/bookings/{bid}/cancel", headers=h)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
def test_admin_requires_admin_role(client):
    h = auth_header(client, "customer@example.com", "secret123")
    assert client.get("/api/v1/admin/stats", headers=h).status_code == 403


def test_admin_stats(client):
    admin_h = auth_header(client, "admin@admin.com", "admin")
    r = client.get("/api/v1/admin/stats", headers=admin_h)
    assert r.status_code == 200
    body = r.json()
    assert "today_bookings" in body
    assert "revenue" in body
    assert body["customer_count"] >= 2


def test_admin_list_bookings_and_filter(client):
    admin_h = auth_header(client, "admin@admin.com", "admin")
    client.post("/api/v1/bookings/create", json=booking_payload())
    r = client.get("/api/v1/admin/bookings", headers=admin_h)
    assert r.status_code == 200
    assert len(r.json()) >= 1
    # Filter by payment status
    paid = client.get("/api/v1/admin/bookings?payment_status=paid", headers=admin_h)
    assert paid.status_code == 200


def test_admin_update_booking_status(client):
    admin_h = auth_header(client, "admin@admin.com", "admin")
    created = client.post("/api/v1/bookings/create", json=booking_payload()).json()
    ref = created["booking_reference"]
    bookings = client.get("/api/v1/admin/bookings", headers=admin_h).json()
    bid = next(b["id"] for b in bookings if b["booking_reference"] == ref)
    r = client.patch(f"/api/v1/admin/bookings/{bid}", json={"booking_status": "confirmed"}, headers=admin_h)
    assert r.status_code == 200
    assert r.json()["booking_status"] == "confirmed"


def test_admin_settings_get_and_update(client):
    admin_h = auth_header(client, "admin@admin.com", "admin")
    r = client.get("/api/v1/admin/settings", headers=admin_h)
    assert r.status_code == 200
    updated = client.put("/api/v1/admin/settings", json={"minimum_booking_notice_hours": 4}, headers=admin_h)
    assert updated.status_code == 200
    assert updated.json()["minimum_booking_notice_hours"] == 4


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------
def test_list_drivers_requires_admin(client):
    h = auth_header(client, "customer@example.com", "secret123")
    assert client.get("/api/v1/admin/drivers", headers=h).status_code == 403


def test_list_drivers_returns_active_drivers(client):
    admin_h = auth_header(client, "admin@admin.com", "admin")
    r = client.get("/api/v1/admin/drivers", headers=admin_h)
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 1
    assert body[0]["name"] == "Ahmed Ali"
    assert body[0]["vehicle"]["make"] == "Mercedes"


def test_create_driver_success(client):
    admin_h = auth_header(client, "admin@admin.com", "admin")
    payload = {
        "first_name": "James",
        "last_name": "Smith",
        "phone": "07112223333",
        "email": "james@test.com",
        "status": "available",
        "vehicle": {
            "vehicle_class_id": 2,
            "registration_number": "JS99ABC",
            "make": "BMW",
            "model": "X5",
            "year": 2023,
            "colour": "Silver",
            "seats": 5
        }
    }
    r = client.post("/api/v1/admin/drivers", json=payload, headers=admin_h)
    assert r.status_code == 200
    body = r.json()
    assert body["first_name"] == "James"
    assert body["vehicle"]["make"] == "BMW"


def test_create_driver_requires_vehicle_class(client):
    admin_h = auth_header(client, "admin@admin.com", "admin")
    payload = {
        "first_name": "No",
        "last_name": "Vehicle",
        "phone": "07112223333",
        "status": "available",
        "vehicle": {
            "vehicle_class_id": 999,
            "registration_number": "BAD999",
            "make": "Ford",
            "model": "Focus"
        }
    }
    r = client.post("/api/v1/admin/drivers", json=payload, headers=admin_h)
    assert r.status_code == 400


def test_get_driver_detail(client):
    admin_h = auth_header(client, "admin@admin.com", "admin")
    r = client.get("/api/v1/admin/drivers/1", headers=admin_h)
    assert r.status_code == 200
    body = r.json()
    assert body["first_name"] == "Ahmed"


def test_update_driver(client):
    admin_h = auth_header(client, "admin@admin.com", "admin")
    r = client.put("/api/v1/admin/drivers/1", json={"status": "busy", "notes": "Updated note"}, headers=admin_h)
    assert r.status_code == 200
    assert r.json()["status"] == "busy"
    assert r.json()["notes"] == "Updated note"


def test_deactivate_driver(client):
    admin_h = auth_header(client, "admin@admin.com", "admin")
    r = client.delete("/api/v1/admin/drivers/1", headers=admin_h)
    assert r.status_code == 200
    assert "deactivated" in r.json()["message"].lower()
    
    r2 = client.get("/api/v1/admin/drivers", headers=admin_h)
    assert r2.status_code == 200
    ids = [d["id"] for d in r2.json()]
    assert 1 not in ids


def test_assign_driver_to_booking(client):
    admin_h = auth_header(client, "admin@admin.com", "admin")
    client.post("/api/v1/bookings/create", json=booking_payload())
    bookings = client.get("/api/v1/admin/bookings", headers=admin_h).json()
    bid = bookings[0]["id"]
    r = client.patch(f"/api/v1/admin/bookings/{bid}/assign-driver?driver_id=1", headers=admin_h)
    assert r.status_code == 200
    body = r.json()
    assert body["driver_name"] == "Ahmed Ali"
    assert body["vehicle_make"] == "Mercedes"
