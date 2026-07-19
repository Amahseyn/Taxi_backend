import datetime
import zoneinfo
import httpx
from sqlalchemy.orm import Session
from app.models import PricingRule, Airport, Vehicle, Settings
from app.config import settings

def get_business_local_time(tz_name: str = "Europe/London") -> datetime.datetime:
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = zoneinfo.ZoneInfo("Europe/London")
    return datetime.datetime.now(tz)

def parse_travel_datetime(date_str: str, time_str: str, tz_name: str = "Europe/London") -> datetime.datetime:
    """
    date_str: YYYY-MM-DD
    time_str: HH:MM
    """
    try:
        dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        tz = zoneinfo.ZoneInfo(tz_name)
        return dt.replace(tzinfo=tz)
    except Exception as e:
        raise ValueError(f"Invalid date or time format: {e}")

class PricingService:
    @staticmethod
    def check_booking_notice(date_str: str, time_str: str, db: Session) -> tuple[bool, str]:
        """
        Validates minimum booking notice (default 3 hours) in London timezone.
        """
        app_settings = db.query(Settings).first()
        notice_hours = app_settings.minimum_booking_notice_hours if app_settings else 3
        tz_name = app_settings.business_timezone if hasattr(app_settings, 'business_timezone') else "Europe/London"

        try:
            travel_dt = parse_travel_datetime(date_str, time_str, tz_name)
        except ValueError as e:
            return False, str(e)

        now_local = get_business_local_time(tz_name)
        notice_delta = datetime.timedelta(hours=notice_hours)

        if travel_dt < now_local:
            return False, "Requested travel date and time is in the past."

        if travel_dt - now_local < notice_delta:
            return False, f"Please call the office to make an urgent booking. Minimum booking notice is {notice_hours} hours."

        return True, ""

    @staticmethod
    def calculate_distance_matrix(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> tuple[float, float]:
        """
        Calls OpenRouteService matrix/direction to calculate actual route distance (miles) and duration (minutes).
        Fallback to straight-line distance if API fails.
        """
        api_key = settings.OPENROUTE_SERVICE_API_KEY
        if not api_key:
            # Simple fallback (rough estimation)
            import math
            # Haversine formula
            R = 3958.8 # miles
            dlat = math.radians(dest_lat - origin_lat)
            dlng = math.radians(dest_lng - origin_lng)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(origin_lat)) * math.cos(math.radians(dest_lat)) * math.sin(dlng/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            miles = R * c
            # Assume 35mph average
            minutes = (miles / 35.0) * 60.0
            return miles, minutes

        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        headers = {
            "Accept": "application/json, application/geo+json, charset=utf-8",
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
        body = {
            "coordinates": [[origin_lng, origin_lat], [dest_lng, dest_lat]]
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=body, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    route = data["routes"][0]["summary"]
                    distance_meters = route["distance"]
                    duration_seconds = route["duration"]
                    
                    distance_miles = distance_meters * 0.000621371
                    duration_minutes = duration_seconds / 60.0
                    return round(distance_miles, 2), round(duration_minutes, 1)
        except Exception:
            pass

        # Haversine fallback
        import math
        R = 3958.8
        dlat = math.radians(dest_lat - origin_lat)
        dlng = math.radians(dest_lng - origin_lng)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(origin_lat)) * math.cos(math.radians(dest_lat)) * math.sin(dlng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        miles = R * c
        minutes = (miles / 35.0) * 60.0
        return round(miles, 2), round(minutes, 1)

    @staticmethod
    def calculate_quote(
        db: Session,
        journey_type: str,
        pickup_lat: float,
        pickup_lng: float,
        dest_lat: float,
        dest_lng: float,
        vehicle_code: str,
        airport_code: str = None
    ) -> dict:
        """
        Determines and computes the price based on airport vs local pricing rules.
        """
        # Fetch vehicle
        vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code, Vehicle.active == True).first()
        if not vehicle:
            raise ValueError(f"Vehicle type '{vehicle_code}' is not active or does not exist.")

        # Check distance
        distance_miles, duration_minutes = PricingService.calculate_distance_matrix(
            pickup_lat, pickup_lng, dest_lat, dest_lng
        )

        is_airport = "Airport" in journey_type or airport_code is not None
        price = 0.0
        rule_used = None

        if is_airport and airport_code:
            # Query airport rule
            rule = db.query(PricingRule).filter(
                PricingRule.type == "airport",
                PricingRule.airport_code == airport_code,
                PricingRule.active == True
            ).first()
            
            if rule and rule.vehicle_prices and vehicle_code in rule.vehicle_prices:
                price = float(rule.vehicle_prices[vehicle_code])
                rule_used = f"Airport Rule ({airport_code})"
            
        if price == 0.0:
            # Local / Mileage Rule
            rule = db.query(PricingRule).filter(PricingRule.type == "local", PricingRule.active == True).first()
            if not rule:
                # Default pricing fallback if no rule configured
                min_fare = 15.0
                per_mile = 2.5
                multiplier = 1.0
            else:
                min_fare = rule.minimum_fare or 15.0
                per_mile = rule.per_mile_rate or 2.5
                multiplier = rule.vehicle_prices.get(vehicle_code, 1.0) if rule.vehicle_prices else 1.0

            raw_price = min_fare + (distance_miles * per_mile)
            price = round(raw_price * multiplier, 2)
            rule_used = "Local / Mileage Rule"

        return {
            "distance_miles": distance_miles,
            "duration_minutes": duration_minutes,
            "price": price,
            "vehicle_code": vehicle_code,
            "rule_used": rule_used
        }
