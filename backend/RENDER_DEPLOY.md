# Elimu Pro - Backend (Render) Deployment Guide

## Quick Setup via Render Blueprint

1. Go to Render Dashboard → **New +** → **Blueprint**
2. Connect GitHub repo: `derosavage/elimu-pro-kenya-hub`
3. Render will detect `render.yaml` and create:
   - **PostgreSQL database** (`elimupro-db`)
   - **Web Service** (`elimupro-backend`)

4. The blueprint auto-generates `SECRET_KEY` and `JWT_SECRET_KEY`
5. `DATABASE_URL` is automatically linked to the database
6. Set `FRONTEND_URL` to your Vercel frontend URL after deployment

## Manual Setup (Alternative)

### 1. Create PostgreSQL Database
- Render Dashboard → **New +** → **PostgreSQL**
- Name: `elimupro-db`
- Plan: Free
- Region: Oregon (or closest to users)

### 2. Create Web Service
- Render Dashboard → **New +** → **Web Service**
- Connect repo: `derosavage/elimu-pro-kenya-hub`
- Root Directory: `backend`
- Runtime: Python 3
- Build Command: `pip install --no-cache-dir -r requirements.txt`
- Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --access-logfile - --error-logfile - run:app`
- Health Check Path: `/api/v1/health/ready`

### 3. Environment Variables
| Key | Value |
|-----|-------|
| `SECRET_KEY` | Auto-generate (32+ chars) |
| `JWT_SECRET_KEY` | Auto-generate (32+ chars, different from SECRET_KEY) |
| `DATABASE_URL` | Paste from PostgreSQL "External Database URL" |
| `FRONTEND_URL` | `https://your-frontend.vercel.app` |
| `JWT_ACCESS_HOURS` | `12` |

### 4. Run Migrations (First Deploy Only)
After first deploy, in Render Shell:
```bash
flask --app run:app db upgrade
```

Or add a one-time job in render.yaml for migrations.

## API Endpoints

Base: `https://your-backend.onrender.com/api/v1`

- `GET /health` — Health check
- `GET /health/ready` — Readiness (DB check)
- `POST /auth/register` — Student registration
- `POST /auth/login` — Login
- `GET /auth/me` — Current user
- `POST /auth/change-password` — Change password

Plus: `/schools`, `/admissions`, `/students`, `/academics`, `/finance`, `/announcements`, `/teachers`, `/parents`

## CORS Configuration

Backend allows origins from `FRONTEND_URL` (comma-separated). Ensure Vercel frontend URL is set.

## Troubleshooting

- **Build fails**: Check Python version (3.12), ensure requirements.txt is valid
- **DB connection fails**: Verify DATABASE_URL format: `postgresql+psycopg://user:pass@host:5432/db`
- **CORS errors**: Check FRONTEND_URL matches Vercel deployment exactly
- **Migration needed**: Run `flask db upgrade` in Render shell