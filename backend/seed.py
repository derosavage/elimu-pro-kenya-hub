"""Create tables (if missing) and load DEMO data into an EMPTY database."""
from app import create_app
from app.extensions import db
from app.models import School
from app.seed import seed_demo, DEMO_PASSWORD

app = create_app()
with app.app_context():
    db.create_all()
    if School.query.count():
        raise SystemExit("Database already contains schools; refusing to seed demo data.")
    seed_demo()
    print("Demo data loaded. Password for all demo accounts:", DEMO_PASSWORD)
    print("  Super admin : super@elimupro.demo")
    print("  School admin: admin@mwangaza.demo")
    print("  Bursar      : bursar@mwangaza.demo")
    print("  Teacher     : teacher@mwangaza.demo")
    print("  Student     : achieng@mwangaza.demo")
