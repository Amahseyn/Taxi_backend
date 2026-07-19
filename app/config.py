import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Colchester Taxi Booking System"
    DATABASE_URL: str = "sqlite:////Users/mo/Projects/Taxi/taxi.db"
    JWT_SECRET: str = "supersecretkeychangeinprod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 1 day

    # External APIs
    OPENROUTE_SERVICE_API_KEY: str = "5b3ce3597851110001cf6248eeeba7a54c9f47acbb3be51a7877c0b9"
    GOOGLE_MAPS_API_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # SMTP for Emails
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@colchesterairporttaxi.co.uk"

    # Business Constraints
    BUSINESS_TIMEZONE: str = "Europe/London"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
