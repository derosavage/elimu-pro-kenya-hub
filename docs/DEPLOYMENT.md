# Deployment notes

Nothing in this project has been deployed by the author of this package. These are the intended steps.

## Backend on AlwaysData (Flask + MySQL)
1. Create a MySQL database in the AlwaysData panel and import `database/schema.sql` (phpMyAdmin or `mysql` client).
2. Upload `backend/` (Git or SFTP), create a virtualenv and `pip install -r requirements.txt`.
3. Add a **WSGI site**: application path `run:app` (module `run.py`, object `app`), pointing at your virtualenv.
4. Set environment variables in the site configuration: `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`
   (`mysql+pymysql://user:pass@mysql-ACCOUNT.alwaysdata.net/ACCOUNT_elimupro`), `FRONTEND_URL` (your Vercel URL, no trailing slash).
5. Create the first super admin and school **without demo data**, for example in a Flask shell:
   create a `User(role="super_admin", school_id=None, ...)` and call `set_password(...)`. Do not run `seed.py` in production.

## Frontend on Vercel
1. Import the repo, set **Root Directory** to `frontend`, framework preset "Create React App".
2. Set `REACT_APP_API_URL` to `https://YOUR-BACKEND/api`. `vercel.json` already rewrites all routes to `index.html`.
3. Serve everything over HTTPS (required for PWA install and service workers).

## M-Pesa (Daraja) - NOT live-tested
Set `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_SHORTCODE`, `MPESA_PASSKEY`, `MPESA_CALLBACK_URL` (and `MPESA_ENV=production` for live).
`POST /api/payments/mpesa/stk-push` will then call Daraja. **Still to build before real use:** a public callback endpoint that verifies the
Safaricom result, matches it to the request, creates the `Payment` (idempotently) and issues a receipt. Until then, record payments manually.

## Before going live checklist
Strong random secrets · HTTPS only · no demo data · database backups · rate limiting on `/api/auth/*` (not implemented) ·
password reset flow (not implemented) · review CORS origin · run the tests against MySQL.
