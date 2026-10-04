"""DEV ONLY: drops every table and reloads demo data. Refuses if any non-demo school exists."""
from app import create_app
from app.extensions import db
from app.models import School
from app.seed import seed_demo, DEMO_PASSWORD

app = create_app()
with app.app_context():
    real = School.query.filter_by(is_demo=False).count()
    if real:
        raise SystemExit(f"{real} non-demo school(s) found; refusing to wipe the database.")
    if input("This DELETES all data in the configured database. Type YES to continue: ") != "YES":
        raise SystemExit("Cancelled.")
    db.drop_all()
    db.create_all()
    seed_demo()
    print("Demo data reloaded. Password for all demo accounts:", DEMO_PASSWORD)