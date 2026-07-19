# Taxi Backend API

FastAPI backend for Colchester Airport Taxi booking system.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the server

```bash
uvicorn app.main:app --reload
```

## API Endpoints

- `GET /` - Health check
- `GET /api/v1/airports` - List airports
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/bookings` - Create booking
- `GET /api/v1/admin/bookings` - List all bookings (admin only)
- `PATCH /api/v1/admin/bookings/{id}` - Update booking (admin only)

## Database Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Testing

```bash
pytest tests/
```

## Environment Variables

Create a `.env` file with:

```
DATABASE_URL=sqlite:///./taxi.db
SECRET_KEY=your-secret-key
STRIPE_API_KEY=sk_test_...
TWILIO_ACCOUNT_SID=...
```