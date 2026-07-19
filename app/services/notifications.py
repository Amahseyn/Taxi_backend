import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client as TwilioClient
from app.config import settings

class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, html_content: str) -> bool:
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            print(f"[MOCK EMAIL] To: {to_email}\nSubject: {subject}\nContent:\n{html_content[:300]}...\n")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM
            msg["To"] = to_email

            part = MIMEText(html_content, "html")
            msg.attach(part)

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
            
            print(f"Email successfully sent to {to_email}")
            return True
        except Exception as e:
            print(f"ERROR: EmailService failed to send email to {to_email}: {e}")
            return False

    @staticmethod
    def notify_customer_booking(customer_email: str, details: dict):
        subject = f"Booking Confirmation: {details['booking_reference']}"
        html = f"""
        <h2>Your Taxi Booking is Confirmed!</h2>
        <p><strong>Reference:</strong> {details['booking_reference']}</p>
        <p><strong>Journey:</strong> {details['pickup_address']} to {details['destination_address']}</p>
        <p><strong>Date & Time:</strong> {details['travel_date']} at {details['travel_time']}</p>
        <p><strong>Vehicle:</strong> {details['vehicle_name']}</p>
        <p><strong>Price:</strong> £{details['price']}</p>
        <p><strong>Payment Status:</strong> {details['payment_status']}</p>
        <p>Thank you for choosing Colchester Airport Taxi.</p>
        """
        EmailService.send_email(customer_email, subject, html)

    @staticmethod
    def notify_business_new_booking(details: dict):
        subject = f"NEW BOOKING: {details['booking_reference']}"
        html = f"""
        <h2>New Taxi Booking Received</h2>
        <p><strong>Reference:</strong> {details['booking_reference']}</p>
        <p><strong>Customer:</strong> {details['customer_name']} ({details['customer_phone']})</p>
        <p><strong>Journey:</strong> {details['pickup_address']} to {details['destination_address']}</p>
        <p><strong>Date & Time:</strong> {details['travel_date']} at {details['travel_time']}</p>
        <p><strong>Vehicle:</strong> {details['vehicle_name']}</p>
        <p><strong>Price:</strong> £{details['price']}</p>
        """
        EmailService.send_email(settings.SMTP_FROM, subject, html)


class SMSService:
    @staticmethod
    def send_sms(to_phone: str, message: str) -> bool:
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            print(f"[MOCK SMS] To: {to_phone}\nMessage: {message}\n")
            return True

        try:
            client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to_phone
            )
            print(f"SMS successfully sent to {to_phone}")
            return True
        except Exception as e:
            print(f"ERROR: SMSService failed to send SMS to {to_phone}: {e}")
            return False

    @staticmethod
    def notify_customer_booking_sms(to_phone: str, details: dict):
        msg = (
            f"Colchester Taxi Confirmed. Ref: {details['booking_reference']}. "
            f"Date: {details['travel_date']} {details['travel_time']}. "
            f"Pickup: {details['pickup_address']}. "
            f"Dest: {details['destination_address']}. Price: £{details['price']}."
        )
        SMSService.send_sms(to_phone, msg)
