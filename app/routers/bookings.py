import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Booking, Customer, Vehicle, Payment, Settings
from app.schemas import QuoteRequest, QuoteResponse, BookingCreate, BookingOut, BookingDetailOut
from app.services.pricing_service import PricingService
from app.services.stripe_service import StripeService
from app.services.notifications import EmailService, SMSService
from app.routers.dependencies import get_current_user, get_current_admin
import datetime
import zoneinfo

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.post("/quote", response_model=QuoteResponse)
def get_quote(payload: QuoteRequest, db: Session = Depends(get_db)):
    # 1. Check notice rules
    allowed, reason = PricingService.check_booking_notice(payload.travel_date, payload.travel_time, db)
    
    # Calculate pricing
    try:
        quote = PricingService.calculate_quote(
            db=db,
            journey_type=payload.journey_type,
            pickup_lat=payload.pickup_lat,
            pickup_lng=payload.pickup_lng,
            dest_lat=payload.destination_lat,
            dest_lng=payload.destination_lng,
            vehicle_code=payload.vehicle_code,
            airport_code=payload.airport_code
        )
        return {
            "distance_miles": quote["distance_miles"],
            "duration_minutes": quote["duration_minutes"],
            "price": quote["price"],
            "vehicle_code": payload.vehicle_code,
            "notice_allowed": allowed,
            "notice_reason": reason
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/create")
def create_booking(
    payload: BookingCreate,
    req: Request,
    db: Session = Depends(get_db),
    # Optional dependency to link booking to user if they are logged in
    token: Optional[str] = None
):
    # 1. Check notice rules
    allowed, reason = PricingService.check_booking_notice(payload.travel_date, payload.travel_time, db)
    if not allowed:
        raise HTTPException(status_code=400, detail=reason)

    # 2. Get customer or create if not exist
    # Attempt to resolve current user from authorization header if present
    current_user_id = None
    auth_header = req.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            from app.routers.dependencies import get_current_user
            token = auth_header.split(" ")[1]
            user = get_current_user(token=token, db=db)
            current_user_id = user.id
        except Exception:
            pass

    customer = db.query(Customer).filter(Customer.email == payload.email).first()
    if not customer:
        customer = Customer(
            user_id=current_user_id,
            name=payload.name,
            email=payload.email,
            phone=payload.phone
        )
        db.add(customer)
        db.flush()
    elif current_user_id and not customer.user_id:
        customer.user_id = current_user_id
        db.add(customer)
        db.flush()

    # 3. Get pricing quote
    try:
        quote = PricingService.calculate_quote(
            db=db,
            journey_type=payload.journey_type,
            pickup_lat=payload.pickup_lat,
            pickup_lng=payload.pickup_lng,
            dest_lat=payload.destination_lat,
            dest_lng=payload.destination_lng,
            vehicle_code=payload.vehicle_code,
            airport_code=payload.airport_code
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    vehicle = db.query(Vehicle).filter(Vehicle.code == payload.vehicle_code).first()
    
    # 4. Generate unique reference
    booking_reference = f"TX-{uuid.uuid4().hex[:8].upper()}"

    # 5. Save booking details
    booking = Booking(
        booking_reference=booking_reference,
        customer_id=customer.id,
        journey_type=payload.journey_type,
        pickup_address=payload.pickup_address,
        pickup_postcode=payload.pickup_postcode,
        pickup_lat=payload.pickup_lat,
        pickup_lng=payload.pickup_lng,
        destination_address=payload.destination_address,
        destination_postcode=payload.destination_postcode,
        destination_lat=payload.destination_lat,
        destination_lng=payload.destination_lng,
        airport_code=payload.airport_code,
        terminal=payload.terminal,
        flight_number=payload.flight_number,
        vehicle_id=vehicle.id,
        passengers=payload.passengers,
        large_luggage=payload.large_luggage,
        small_luggage=payload.small_luggage,
        distance_miles=quote["distance_miles"],
        duration_minutes=quote["duration_minutes"],
        price=quote["price"],
        payment_method="stripe",
        payment_status="pending",
        booking_status="pending",
        travel_date=payload.travel_date,
        travel_time=payload.travel_time,
        return_journey_data=payload.return_journey_data.model_dump() if payload.return_journey_data else None
    )
    db.add(booking)
    db.flush()

    # 6. Create Stripe checkout session
    origin_header = req.headers.get("origin") or "http://localhost:3000"
    success_url = f"{origin_header}/booking/confirmation?ref={booking_reference}"
    cancel_url = f"{origin_header}/booking?step=payment"

    session = StripeService.create_checkout_session(
        booking_ref=booking_reference,
        amount=quote["price"],
        customer_email=payload.email,
        success_url=success_url,
        cancel_url=cancel_url
    )

    # Save payment log
    payment = Payment(
        booking_id=booking.id,
        amount=quote["price"],
        stripe_session_id=session.get("id") if hasattr(session, "id") else session["id"],
        status="pending"
    )
    db.add(payment)
    db.commit()

    return {
        "booking_reference": booking_reference,
        "price": quote["price"],
        "stripe_session_url": session.get("url") if hasattr(session, "url") else session["url"]
    }

@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = StripeService.verify_webhook(payload.decode("utf-8"), sig_header or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Process successful payment event
    event_type = event.get("type")
    
    # Handle checkout.session.completed or mock hook
    if event_type in ["checkout.session.completed", "payment_intent.succeeded"]:
        session_data = event.get("data", {}).get("object", {})
        booking_ref = session_data.get("metadata", {}).get("booking_reference")
        payment_intent = session_data.get("payment_intent") or session_data.get("id")
        
        # Fallback for mock setup
        if not booking_ref:
            booking_ref = session_data.get("client_reference_id")
            
        if booking_ref:
            # Load Booking
            booking = db.query(Booking).filter(Booking.booking_reference == booking_ref).first()
            if booking and booking.payment_status != "paid":
                booking.payment_status = "paid"
                booking.booking_status = "confirmed"
                
                # Increment customer total bookings
                customer = db.query(Customer).filter(Customer.id == booking.customer_id).first()
                if customer:
                    customer.total_bookings += 1
                
                # Update Payment record
                payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
                if payment:
                    payment.status = "paid"
                    payment.stripe_payment_intent_id = payment_intent
                
                db.commit()
                
                # Send notifications resiliently
                notif_details = {
                    "booking_reference": booking.booking_reference,
                    "customer_name": customer.name if customer else "Customer",
                    "customer_phone": customer.phone if customer else "",
                    "pickup_address": booking.pickup_address,
                    "destination_address": booking.destination_address,
                    "travel_date": booking.travel_date,
                    "travel_time": booking.travel_time,
                    "vehicle_name": booking.vehicle.name if booking.vehicle else "Standard",
                    "price": booking.price,
                    "payment_status": "Paid"
                }
                
                EmailService.notify_customer_booking(booking.customer.email, notif_details)
                EmailService.notify_business_new_booking(notif_details)
                SMSService.notify_customer_booking_sms(booking.customer.phone, notif_details)

    return {"status": "success"}

@router.get("/my-bookings", response_model=List[BookingOut])
def get_my_bookings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
    if not customer:
        return []
    return db.query(Booking).filter(Booking.customer_id == customer.id).order_by(Booking.created_at.desc()).all()

@router.post("/{booking_id}/cancel")
def cancel_booking(booking_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Verify booking ownership
    customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
    if not customer:
        raise HTTPException(status_code=403, detail="Customer profile not found.")
        
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.customer_id == customer.id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    # Check cancellation window
    app_settings = db.query(Settings).first()
    window_hours = app_settings.cancellation_window_hours if app_settings else 24

    # Calculate travel datetime in local timezone
    tz_name = "Europe/London"
    travel_dt = PricingService.check_booking_notice(booking.travel_date, booking.travel_time, db)
    
    # Better direct travel datetime parsing
    try:
        travel_dt = datetime.datetime.strptime(f"{booking.travel_date} {booking.travel_time}", "%Y-%m-%d %H:%M")
        tz = zoneinfo.ZoneInfo(tz_name)
        travel_dt = travel_dt.replace(tzinfo=tz)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking date/time on record.")

    now_local = datetime.datetime.now(zoneinfo.ZoneInfo(tz_name))
    if travel_dt - now_local < datetime.timedelta(hours=window_hours):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Please contact the office. Bookings cannot be cancelled online within {window_hours} hours of travel."
        )

    booking.booking_status = "cancelled"
    db.commit()
    return {"status": "success", "message": "Booking has been cancelled."}

@router.post("/{booking_id}/amend-request")
def request_amendment(booking_id: int, details: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
    if not customer:
        raise HTTPException(status_code=403, detail="Customer profile not found.")
        
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.customer_id == customer.id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    # Create business email notification about amendment
    subject = f"AMENDMENT REQUEST: {booking.booking_reference}"
    html = f"""
    <h2>Amendment Request for Booking {booking.booking_reference}</h2>
    <p><strong>Customer:</strong> {customer.name} ({customer.phone})</p>
    <p><strong>Requested Changes:</strong></p>
    <p>{details.get('message', 'No details provided.')}</p>
    """
    EmailService.send_email(settings.SMTP_FROM, subject, html)
    return {"status": "success", "message": "Amendment request has been sent to the office."}
