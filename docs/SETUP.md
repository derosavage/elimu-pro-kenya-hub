# Local setup

## Prerequisites
Python 3.10+, Node.js 18+, and PostgreSQL 15+ are required. Docker Desktop can provide PostgreSQL and run the full stack instead.

## PostgreSQL
Create an empty local database, for example with `createdb elimupro`. Apply the committed schema revisions from `backend/` after configuring the environment:

```bash
flask --app run:app db upgrade
```

`database/schema.sql` is a generated PostgreSQL reference, not the production migration mechanism. After changing models, create and review a revision with `flask --app run:app db migrate -m "describe change"` and commit the resulting file under `backend/migrations/versions/`.

## Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # Windows: Copy-Item .env.example .env
```

Set distinct random `SECRET_KEY` and `JWT_SECRET_KEY` values (at least 32 characters), and update `DATABASE_URL` to your PostgreSQL database. For local PostgreSQL use `postgresql+psycopg://USER:PASSWORD@localhost:5432/elimupro`; URL-encode special characters in credentials. Set `FRONTEND_URL=http://localhost:3000`.

Run `flask --app run:app db upgrade`, then optionally load demo data into a fresh development database with `python seed.py`. Start the API with `python run.py`; liveness is at `http://localhost:5000/api/v1/health` and database readiness is at `http://localhost:5000/api/v1/health/ready`.

## Frontend
```bash
cd frontend
cp .env.example .env
npm ci
npm start
```

The frontend runs at `http://localhost:3000`; its default API URL is `http://localhost:5000/api/v1`.

## Docker
From the repository root, copy `.env.example` to `.env`, replace all development-only secrets, and run `docker compose up --build`. The app is served at `http://localhost:8080`; Compose starts PostgreSQL, applies migrations once, then starts Flask and Nginx.

## Tests
From `backend/`, run `python -m pytest -q`. Tests use in-memory SQLite and do not require PostgreSQL credentials.

## Troubleshooting
- **Missing environment variable or weak secret**: create `backend/.env` from `backend/.env.example`; use two distinct secrets of at least 32 characters.
- **CORS error**: `FRONTEND_URL` must exactly match the browser-visible origin, including scheme, host, and port.
- **Cannot reach API**: verify `REACT_APP_API_URL` and restart the frontend after changing its environment file.
- **PostgreSQL connection error**: verify the database URL, network access, TLS requirements, and percent-encoding of username/password characters.
- **Seed reports existing schools**: intentional safety check; use a fresh development database.
- **Signup shows no schools**: no active school with admissions open exists; log in as super admin and create one.
