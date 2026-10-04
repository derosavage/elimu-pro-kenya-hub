# Deployment guide

## Architecture
Use Vercel for the React frontend and Supabase for managed PostgreSQL. Supabase is the database platform; it does not run this Flask/WSGI application. Deploy the Flask container to a container runtime such as Render, Railway, Fly.io, or Cloud Run, and configure it to connect to Supabase.

## Supabase PostgreSQL
1. Create a Supabase project and copy its PostgreSQL connection URI. Use the direct connection when the runtime supports its network requirements, otherwise choose the appropriate Supabase pooler connection mode.
2. Configure the backend `DATABASE_URL` with that URI and `sslmode=require`. The application normalizes `postgres://` and `postgresql://` URIs to the installed psycopg 3 driver.
3. Configure `SECRET_KEY` and `JWT_SECRET_KEY` as different random values of at least 32 characters, and set `FRONTEND_URL` to the exact Vercel origin.
4. Run `flask --app run:app db upgrade` as a release/migration step from the `backend/` directory before routing traffic to the new version. Do not use demo seed scripts in production.

The schema migration creates PostgreSQL tables; it does not transfer rows from an existing MySQL database. If production data already exists, take a verified backup, transform/export/import it into PostgreSQL, and reconcile row counts and key relationships before switching traffic.

## Flask API container
Build from `backend/Dockerfile`. Set the runtime start command to the image default, which runs Gunicorn on port `5000`. Configure the platform health check to `GET /api/v1/health/ready`; this returns success only when the database is reachable. Use a platform-managed secret store for credentials and keep database network access restricted to the backend runtime.

## Frontend on Vercel
1. Import the repository and set **Root Directory** to `frontend` with the Create React App preset.
2. Set `REACT_APP_API_URL` to `https://YOUR-BACKEND/api/v1` for the Production, Preview, and Development environments as appropriate.
3. `vercel.json` rewrites client-side routes to `index.html`. Set the backend CORS `FRONTEND_URL` to the exact deployed origin and use HTTPS.

## Docker Compose
For local full-stack runs, copy the root `.env.example` to `.env`, change its development-only values, and run `docker compose up --build`. Compose provides local PostgreSQL, runs migrations once before the API, and serves the app through Nginx at `http://localhost:8080`. Production Supabase deployments should use the platform's PostgreSQL URI and release migration step instead of the Compose database service.

## M-Pesa and launch checklist
Daraja STK Push has not been live-tested. Before accepting real payments, implement and verify an idempotent public callback that validates Safaricom results, associates them with the request, records payments, and issues receipts. Until then, payments must be recorded manually.

Before launch, use HTTPS, strong distinct secrets, production CORS origins, database backups, no demo data, monitoring, and a rollback plan. Rate limiting and password reset are not implemented; run the automated suite before each release. The parent/student/teacher business-flow suite uses SQLite; a live PostgreSQL smoke test is still required in the target environment.
