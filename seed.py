import sys
import os

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, engine, SessionLocal
from app.models import User, Customer, Vehicle, Airport, PricingRule, Settings, Driver, DriverVehicle
from app.core.auth import get_password_hash

def seed_database():
    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Ensure an easy-access admin account exists (idempotent).
        admin_email = "admin@admin.com"
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            admin_user = User(
                email=admin_email,
                password_hash=get_password_hash("admin"),
                role="admin"
            )
            db.add(admin_user)
            db.flush()
            db.add(Customer(
                user_id=admin_user.id,
                name="admin",
                email=admin_email,
                phone="+44 1206 555555"
            ))
            db.commit()
            print("Created admin user (email: admin@admin.com / password: admin).")

        # Check if users already seeded
        if db.query(User).first():
            print("Database already seeded.")
            return

        print("Seeding database...")
        
        # 1. Create Default Admin User
        admin_user = User(
            email="admin@colchesterairporttaxi.co.uk",
            password_hash=get_password_hash("AdminColchester123!"),
            role="admin"
        )
        db.add(admin_user)
        db.flush() # Populate ID

        admin_customer = Customer(
            user_id=admin_user.id,
            name="Office Admin",
            email="admin@colchesterairporttaxi.co.uk",
            phone="+44 1206 555555"
        )
        db.add(admin_customer)
        
        # 2. Create Vehicles
        vehicles = [
            Vehicle(name="Saloon", code="saloon", max_passengers=4, large_luggage_capacity=2, small_luggage_capacity=2, active=True),
            Vehicle(name="Estate", code="estate", max_passengers=4, large_luggage_capacity=3, small_luggage_capacity=3, active=True),
            Vehicle(name="Executive", code="executive", max_passengers=4, large_luggage_capacity=2, small_luggage_capacity=2, active=True),
            Vehicle(name="Minibus", code="minibus", max_passengers=8, large_luggage_capacity=8, small_luggage_capacity=8, active=True),
        ]
        for v in vehicles:
            db.add(v)
            
        # 3. Create Airports
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
            
        # 4. Create Settings
        app_settings = Settings(
            business_name="Colchester Airport Taxi",
            phone="+44 1206 555555",
            email="bookings@colchesterairporttaxi.co.uk",
            minimum_booking_notice_hours=3,
            cancellation_window_hours=24,
            stripe_enabled=True,
            sms_enabled=True
        )
        db.add(app_settings)
        
        # 5. Create Drivers and Vehicles
        drivers_data = [
            {
                "first_name": "Ahmed", "last_name": "Ali", "phone": "07123456789", "email": "ahmed@test.com",
                "status": "available", "notes": "Executive specialist",
                "vehicle": {"vehicle_class_id": 3, "registration_number": "AB12CDE", "make": "Mercedes", "model": "E-Class", "year": 2024, "colour": "Black", "seats": 4}
            },
            {
                "first_name": "Sarah", "last_name": "Johnson", "phone": "07987654321", "email": "sarah@test.com",
                "status": "available", "notes": "Friendly local expert",
                "vehicle": {"vehicle_class_id": 1, "registration_number": "XY34ZZA", "make": "Toyota", "model": "Prius", "year": 2023, "colour": "White", "seats": 4}
            },
            {
                "first_name": "Mohammed", "last_name": "Khan", "phone": "07001112222", "email": "mohammed@test.com",
                "status": "busy", "notes": "Airport transfers",
                "vehicle": {"vehicle_class_id": 4, "registration_number": "MP99BUS", "make": "Ford", "model": "Transit", "year": 2022, "colour": "Blue", "seats": 8}
            }
        ]
        
        vehicle_classes = {v.code: v for v in db.query(Vehicle).all()}
        
        for d in drivers_data:
            driver = Driver(
                first_name=d["first_name"],
                last_name=d["last_name"],
                phone=d["phone"],
                email=d["email"],
                status=d["status"],
                notes=d["notes"],
                active=True
            )
            db.add(driver)
            db.flush()
            
            v_data = d["vehicle"]
            driver_vehicle = DriverVehicle(
                driver_id=driver.id,
                vehicle_class_id=v_data["vehicle_class_id"],
                registration_number=v_data["registration_number"],
                make=v_data["make"],
                model=v_data["model"],
                year=v_data["year"],
                colour=v_data["colour"],
                seats=v_data["seats"]
            )
            db.add(driver_vehicle)
        
        # 6. Create Pricing Rules (Matching frontend calculator values)
        # Type: "airport"
        airport_prices = [
            # airport_code, saloon, estate, executive, minibus
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
            rule = PricingRule(
                type="airport",
                airport_code=code,
                vehicle_prices={
                    "saloon": saloon,
                    "estate": estate,
                    "executive": exec_p,
                    "minibus": minibus
                },
                active=True
            )
            db.add(rule)
            
        # Add a local mileage pricing rule
        local_rule = PricingRule(
            type="local",
            minimum_fare=15.0,
            per_mile_rate=2.5,
            vehicle_prices={
                "saloon": 1.0,      # multiplier
                "estate": 1.2,      # multiplier
                "executive": 1.4,   # multiplier
                "minibus": 1.8      # multiplier
            },
            active=True
        )
        db.add(local_rule)
        
        db.commit()
        print("Database seeded successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
