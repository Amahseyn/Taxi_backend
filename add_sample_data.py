import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, engine, SessionLocal
from app.models import User, Customer, Vehicle, Airport, PricingRule, Settings, Driver, DriverVehicle, Booking, Payment
from app.core.auth import get_password_hash
import datetime
import zoneinfo

def seed_all():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Ensure admin exists
        admin_email = "admin@admin.com"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(email=admin_email, password_hash=get_password_hash("admin"), role="admin")
            db.add(admin)
            db.flush()
            db.add(Customer(user_id=admin.id, name="admin", email=admin_email, phone="+44 1206 555555"))

        # Vehicles
        if db.query(Vehicle).count() == 0:
            vehicles = [
                Vehicle(name="Saloon", code="saloon", max_passengers=4, large_luggage_capacity=2, small_luggage_capacity=2, active=True),
                Vehicle(name="Estate", code="estate", max_passengers=4, large_luggage_capacity=3, small_luggage_capacity=3, active=True),
                Vehicle(name="Executive", code="executive", max_passengers=4, large_luggage_capacity=2, small_luggage_capacity=2, active=True),
                Vehicle(name="Minibus", code="minibus", max_passengers=8, large_luggage_capacity=8, small_luggage_capacity=8, active=True),
            ]
            for v in vehicles:
                db.add(v)

        # Airports
        if db.query(Airport).count() == 0:
            airports = [
                Airport(code="STN", name="Stansted", city="London", active=True),
                Airport(code="SEN", name="Southend", city="Southend-on-Sea", active=True),
                Airport(code="LCY", name="London City", city="London", active=True),
                Airport(code="NWI", name="Norwich", city="Norwich", active=True),
                Airport(code="LHR", name="Heathrow", city="London", active=True),
                Airport(code="LGW", name="Gatwick", city="London", active=True),
                Airport(code="LTN", name="Luton", city="London", active=True),
                Airport(code="BHX", name="Birmingham", city="Birmingham", active=True),
                Airport(code="EMA", name="East Midlands", city="Derby", active=True),
                Airport(code="LBA", name="Leeds/Bradford", city="Leeds", active=True),
                Airport(code="MAN", name="Manchester", city="Manchester", active=True),
                Airport(code="LPL", name="Liverpool", city="Liverpool", active=True),
            ]
            for a in airports:
                db.add(a)

        # Settings
        if db.query(Settings).count() == 0:
            db.add(Settings(
                business_name="Colchester Airport Taxi",
                phone="+44 1206 555555",
                email="bookings@colchesterairporttaxi.co.uk",
                minimum_booking_notice_hours=3,
                cancellation_window_hours=24,
                stripe_enabled=True,
                sms_enabled=True
            ))

        # Drivers
        if db.query(Driver).count() == 0:
            drivers_data = [
                {"first_name": "Ahmed", "last_name": "Ali", "phone": "07123456789", "email": "ahmed@test.com", "status": "available", "notes": "Executive specialist", "vehicle_class_id": 3, "reg": "AB12CDE", "make": "Mercedes", "model": "E-Class", "year": 2024, "colour": "Black", "seats": 4},
                {"first_name": "Sarah", "last_name": "Johnson", "phone": "07987654321", "email": "sarah@test.com", "status": "available", "notes": "Friendly local expert", "vehicle_class_id": 1, "reg": "XY34ZZA", "make": "Toyota", "model": "Prius", "year": 2023, "colour": "White", "seats": 4},
                {"first_name": "Mohammed", "last_name": "Khan", "phone": "07001112222", "email": "mohammed@test.com", "status": "busy", "notes": "Airport transfers", "vehicle_class_id": 4, "reg": "MP99BUS", "make": "Ford", "model": "Transit", "year": 2022, "colour": "Blue", "seats": 8},
                {"first_name": "James", "last_name": "Smith", "phone": "07112223333", "email": "james@test.com", "status": "available", "notes": "Long distance expert", "vehicle_class_id": 2, "reg": "JS99ABC", "make": "BMW", "model": "X5", "year": 2023, "colour": "Silver", "seats": 5},
                {"first_name": "Emily", "last_name": "Brown", "phone": "07998887766", "email": "emily@test.com", "status": "available", "notes": "Wheelchair accessible", "vehicle_class_id": 4, "reg": "EB66WCH", "make": "VW", "model": "Crafter", "year": 2023, "colour": "Grey", "seats": 6},
            ]
            for d in drivers_data:
                driver = Driver(first_name=d["first_name"], last_name=d["last_name"], phone=d["phone"], email=d["email"], status=d["status"], notes=d["notes"], active=True)
                db.add(driver)
                db.flush()
                db.add(DriverVehicle(driver_id=driver.id, vehicle_class_id=d["vehicle_class_id"], registration_number=d["reg"], make=d["make"], model=d["model"], year=d["year"], colour=d["colour"], seats=d["seats"]))

        # Pricing Rules
        if db.query(PricingRule).count() == 0:
            airport_prices = [
                ("STN", 75.0, 85.0, 90.0, 120.0),
                ("SEN", 85.0, 95.0, 100.0, 135.0),
                ("LCY", 125.0, 135.0, 140.0, 150.0),
                ("NWI", 130.0, 140.0, 145.0, 150.0),
                ("LHR", 160.0, 175.0, 175.0, 225.0),
                ("LGW", 160.0, 175.0, 175.0, 225.0),
                ("LTN", 160.0, 175.0, 175.0, 225.0),
                ("BHX", 250.0, 265.0, 270.0, 290.0),
                ("EMA", 250.0, 265.0, 270.0, 290.0),
                ("LBA", 355.0, 365.0, 370.0, 400.0),
                ("MAN", 355.0, 365.0, 370.0, 450.0),
                ("LPL", 370.0, 385.0, 390.0, 470.0),
            ]
            for code, saloon, estate, exec_p, minibus in airport_prices:
                db.add(PricingRule(type="airport", airport_code=code, vehicle_prices={"saloon": saloon, "estate": estate, "executive": exec_p, "minibus": minibus}, active=True))
            db.add(PricingRule(type="local", minimum_fare=15.0, per_mile_rate=2.5, vehicle_prices={"saloon": 1.0, "estate": 1.2, "executive": 1.4, "minibus": 1.8}, active=True))

        db.commit()

        # Sample customers
        sample_customers = []
        if db.query(Customer).filter(Customer.email == "john@example.com").first() is None:
            for i, data in enumerate([
                ("john@example.com", "John Smith", "+44 7700 900001"),
                ("jane@example.com", "Jane Doe", "+44 7700 900002"),
                ("bob@example.com", "Bob Wilson", "+44 7700 900003"),
            ]):
                user = User(email=data[0], password_hash=get_password_hash("password123"), role="customer")
                db.add(user)
                db.flush()
                cust = Customer(user_id=user.id, name=data[1], email=data[0], phone=data[2])
                db.add(cust)
                sample_customers.append(cust)
            db.commit()

        # Sample bookings
        vehicles = {v.code: v for v in db.query(Vehicle).all()}
        customers = {c.email: c for c in db.query(Customer).all()}
        drivers = db.query(Driver).all()

        now = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/London"))

        def future_dt(days, hour, minute):
            dt = now + datetime.timedelta(days=days)
            return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")

        def past_dt(days, hour, minute):
            dt = now - datetime.timedelta(days=days)
            return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")

        sample_bookings = [
            {
                "customer_email": "john@example.com", "vehicle_code": "saloon", "driver": drivers[0] if drivers else None,
                "journey_type": "Airport Drop-off", "pickup": "12 High Street, Colchester", "pickup_post": "CO1 1AA",
                "pickup_lat": 51.896, "pickup_lng": 0.892,
                "dest": "Stansted Airport", "dest_post": "CM24 1QW", "dest_lat": 51.885, "dest_lng": 0.235,
                "airport_code": "STN", "passengers": 2, "large_luggage": 1, "small_luggage": 1,
                "distance": 25.0, "duration": 35.0, "price": 75.0,
                "payment_status": "paid", "booking_status": "confirmed",
                "travel_date": future_dt(3, 10, 0)[0], "travel_time": future_dt(3, 10, 0)[1],
            },
            {
                "customer_email": "jane@example.com", "vehicle_code": "estate", "driver": drivers[1] if len(drivers) > 1 else None,
                "journey_type": "Airport Pickup", "pickup": "Heathrow Terminal 5", "pickup_post": "TW6 2GA",
                "pickup_lat": 51.470, "pickup_lng": -0.487,
                "dest": "45 Queens Road, Colchester", "dest_post": "CO2 7TX", "dest_lat": 51.895, "dest_lng": 0.904,
                "airport_code": "LHR", "passengers": 3, "large_luggage": 2, "small_luggage": 2,
                "distance": 65.0, "duration": 75.0, "price": 175.0,
                "payment_status": "paid", "booking_status": "confirmed",
                "travel_date": future_dt(5, 14, 30)[0], "travel_time": future_dt(5, 14, 30)[1],
            },
            {
                "customer_email": "bob@example.com", "vehicle_code": "minibus", "driver": drivers[2] if len(drivers) > 2 else None,
                "journey_type": "Local Journey", "pickup": "Colchester Zoo", "pickup_post": "CO3 9LL",
                "pickup_lat": 51.874, "pickup_lng": 0.904,
                "dest": "Colchester Railway Station", "dest_post": "CO1 1TF", "dest_lat": 51.901, "dest_lng": 0.893,
                "airport_code": None, "passengers": 6, "large_luggage": 3, "small_luggage": 3,
                "distance": 3.5, "duration": 10.0, "price": 23.75,
                "payment_status": "paid", "booking_status": "completed",
                "travel_date": past_dt(2, 9, 0)[0], "travel_time": past_dt(2, 9, 0)[1],
            },
            {
                "customer_email": "john@example.com", "vehicle_code": "executive", "driver": drivers[0] if drivers else None,
                "journey_type": "Return Journey", "pickup": "Gatwick Airport", "pickup_post": "RH6 0NP",
                "pickup_lat": 51.154, "pickup_lng": -0.182,
                "dest": "Colchester Town Hall", "dest_post": "CO1 1TG", "dest_lat": 51.901, "dest_lng": 0.903,
                "airport_code": "LGW", "passengers": 1, "large_luggage": 1, "small_luggage": 1,
                "distance": 60.0, "duration": 70.0, "price": 175.0,
                "payment_status": "pending", "booking_status": "pending",
                "travel_date": future_dt(7, 11, 0)[0], "travel_time": future_dt(7, 11, 0)[1],
            },
            {
                "customer_email": "jane@example.com", "vehicle_code": "saloon", "driver": drivers[1] if len(drivers) > 1 else None,
                "journey_type": "Long Distance", "pickup": "Colchester", "pickup_post": "CO1 1AA",
                "pickup_lat": 51.896, "pickup_lng": 0.892,
                "dest": "Manchester Piccadilly", "dest_post": "M1 2RE", "dest_lat": 53.477, "dest_lng": -2.231,
                "airport_code": "MAN", "passengers": 2, "large_luggage": 1, "small_luggage": 1,
                "distance": 220.0, "duration": 240.0, "price": 355.0,
                "payment_status": "paid", "booking_status": "completed",
                "travel_date": past_dt(10, 6, 0)[0], "travel_time": past_dt(10, 6, 0)[1],
            },
            {
                "customer_email": "bob@example.com", "vehicle_code": "estate", "driver": None,
                "journey_type": "Airport Drop-off", "pickup": "10 Castle Road, Colchester", "pickup_post": "CO3 3DA",
                "pickup_lat": 51.889, "pickup_lng": 0.904,
                "dest": "London City Airport", "dest_post": "E16 2PX", "dest_lat": 51.505, "dest_lng": 0.055,
                "airport_code": "LCY", "passengers": 2, "large_luggage": 0, "small_luggage": 2,
                "distance": 55.0, "duration": 65.0, "price": 135.0,
                "payment_status": "failed", "booking_status": "cancelled",
                "travel_date": past_dt(5, 8, 0)[0], "travel_time": past_dt(5, 8, 0)[1],
            },
            {
                "customer_email": "john@example.com", "vehicle_code": "minibus", "driver": drivers[2] if len(drivers) > 2 else None,
                "journey_type": "Airport Pickup", "pickup": "Stansted Airport", "pickup_post": "CM24 1QW",
                "pickup_lat": 51.885, "pickup_lng": 0.235,
                "dest": "University of Essex", "dest_post": "CO4 3SQ", "dest_lat": 51.878, "dest_lng": 0.947,
                "airport_code": "STN", "passengers": 8, "large_luggage": 8, "small_luggage": 8,
                "distance": 18.0, "duration": 25.0, "price": 120.0,
                "payment_status": "paid", "booking_status": "confirmed",
                "travel_date": future_dt(1, 16, 0)[0], "travel_time": future_dt(1, 16, 0)[1],
            },
        ]

        for idx, b in enumerate(sample_bookings):
            cust = customers.get(b["customer_email"])
            veh = vehicles.get(b["vehicle_code"])
            if not cust or not veh:
                continue
            ref = f"TX-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{cust.id}-{idx}"
            booking = Booking(
                booking_reference=ref,
                customer_id=cust.id,
                journey_type=b["journey_type"],
                pickup_address=b["pickup"], pickup_postcode=b["pickup_post"],
                pickup_lat=b["pickup_lat"], pickup_lng=b["pickup_lng"],
                destination_address=b["dest"], destination_postcode=b["dest_post"],
                destination_lat=b["dest_lat"], destination_lng=b["dest_lng"],
                airport_code=b["airport_code"],
                vehicle_id=veh.id, driver_id=b["driver"].id if b["driver"] else None,
                passengers=b["passengers"], large_luggage=b["large_luggage"], small_luggage=b["small_luggage"],
                distance_miles=b["distance"], duration_minutes=b["duration"], price=b["price"],
                payment_status=b["payment_status"], booking_status=b["booking_status"],
                travel_date=b["travel_date"], travel_time=b["travel_time"],
            )
            db.add(booking)
            db.flush()
            if b["payment_status"] == "paid":
                db.add(Payment(booking_id=booking.id, amount=b["price"], status="succeeded", stripe_payment_intent_id=f"pi_{ref.lower()}", stripe_session_id=f"cs_{ref.lower()}"))

        db.commit()
        print("Sample data added successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_all()
