# Setup guide (local computer)

## 1. Install prerequisites
- Python 3.10+ (`python --version`), Node.js 18+ (`node --version`), MySQL 8 or MariaDB.

## 2. Create the database
```sql
CREATE DATABASE elimupro CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
Load the tables: `mysql -u USER -p elimupro < database/schema.sql`
(Alternatively `db.create_all()` runs automatically when you execute `python seed.py`.)
`database/schema.sql` is generated from the models: after changing a model run `python export_schema.py` inside `backend/`.
There is no migration tool yet; for schema changes on a live database, write manual `ALTER TABLE` statements.

## 3. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```
Edit `.env`:
- `SECRET_KEY`, `JWT_SECRET_KEY`: long random strings (`python -c "import secrets; print(secrets.token_hex(32))"`)
- `DATABASE_URL=mysql+pymysql://USER:PASSWORD@localhost/elimupro` (URL-encode special characters in the password)
- `FRONTEND_URL=http://localhost:3000`

Load demo data (only into an empty database): `python seed.py`. Start: `python run.py` → http://localhost:5000/api/health

## 4. Frontend
```bash
cd frontend
cp .env.example .env      # REACT_APP_API_URL=http://localhost:5000/api
npm install
npm start                 # http://localhost:3000
```

## 5. Tests
`cd backend && pytest -q` (uses in-memory SQLite, needs no MySQL).

## Troubleshooting
- **"Missing required environment variable"**: `backend/.env` is missing or a value is empty.
- **CORS error in the browser console**: `FRONTEND_URL` must exactly match the frontend origin (scheme, host, port); restart the backend.
- **"Cannot reach the server"**: backend not running or `REACT_APP_API_URL` wrong; restart `npm start` after editing `.env`.
- **`Access denied for user` / cannot connect**: check `DATABASE_URL`, that MySQL is running and the database exists.
- **`cryptography` / `bcrypt` install errors**: upgrade pip (`pip install -U pip`) and use Python 3.10+.
- **Seed says database already contains schools**: intentional safety check; use an empty database.
- **Signup shows no schools**: no active school with admissions open exists; log in as super admin and create one.
