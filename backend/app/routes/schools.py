from flask import Blueprint, request, g
from sqlalchemy import func

from ..extensions import db
from ..models import School, User, Student, StudentApplication, Payment, StudentFee, Term
from ..utils.responses import ok, err
from ..utils.security import roles_required, audit, ADMIN_ROLES
from ..utils.validation import clean, valid_email, password_problem

bp = Blueprint("schools", __name__, url_prefix="/api/schools")

PROFILE_FIELDS = ("name", "motto", "address", "phone", "email", "website", "county", "school_type",
                  "primary_color", "logo_url", "admissions_open")


@bp.get("/public")
def public_schools():
    """Used by the signup form so a student can pick their school."""
    rows = School.query.filter_by(is_active=True, admissions_open=True).order_by(School.name).all()
    return ok([s.to_dict(public=True) for s in rows])


@bp.get("/me")
@roles_required(*ADMIN_ROLES, "bursar", "teacher", "class_teacher", "student", "parent")
def my_school():
    return ok(g.user.school.to_dict(public=g.user.role not in ADMIN_ROLES))


@bp.put("/me")
@roles_required(*ADMIN_ROLES)
def update_my_school():
    d = request.get_json(silent=True) or {}
    s = g.user.school
    for k in PROFILE_FIELDS:
        if k in d:
            setattr(s, k, clean(d[k]) if isinstance(d[k], str) else d[k])
    if not s.name:
        return err("School name is required", 422, {"name": "Required"})
    audit("school.updated", "school", s.id)
    db.session.commit()
    return ok(s.to_dict())


@bp.get("/overview")
@roles_required(*ADMIN_ROLES, "bursar")
def overview():
    sid = g.user.school_id
    term = Term.query.filter_by(school_id=sid, is_current=True).first()
    students = Student.query.filter_by(school_id=sid)
    due = db.session.query(func.coalesce(func.sum(StudentFee.amount_due), 0)).filter_by(
        school_id=sid, term_id=term.id).scalar() if term else 0
    paid = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter_by(
        school_id=sid, term_id=term.id, status="confirmed").scalar() if term else 0
    apps = StudentApplication.query.filter(StudentApplication.school_id == sid,
                                           StudentApplication.status != "draft")
    return ok({
        "school": g.user.school.to_dict(), "is_demo": g.user.school.is_demo,
        "current_term": term.to_dict() if term else None,
        "total_students": students.count(), "active_students": students.filter_by(status="active").count(),
        "new_applications": apps.filter_by(status="submitted").count(),
        "pending_applications": apps.filter(StudentApplication.status.in_(("submitted", "under_review",
                                                                           "changes_required"))).count(),
        "fees_expected": float(due), "fees_collected": float(paid), "fees_outstanding": float(due) - float(paid),
    })


# ---------- platform super admin ----------
@bp.get("")
@roles_required("super_admin")
def list_schools():
    return ok([dict(s.to_dict(), student_count=Student.query.filter_by(school_id=s.id).count())
               for s in School.query.order_by(School.name).all()])


@bp.post("")
@roles_required("super_admin")
def create_school():
    d = request.get_json(silent=True) or {}
    name, slug = clean(d.get("name")), (clean(d.get("slug")) or "").lower()
    email = (clean(d.get("admin_email")) or "").lower()
    e = {}
    if not name:
        e["name"] = "Required"
    if not slug or not slug.replace("-", "").isalnum():
        e["slug"] = "Use letters, numbers and hyphens"
    if not valid_email(email):
        e["admin_email"] = "Valid email required"
    if password_problem(d.get("admin_password")):
        e["admin_password"] = password_problem(d.get("admin_password"))
    if e:
        return err("Please fix the highlighted fields", 422, e)
    if School.query.filter_by(slug=slug).first() or User.query.filter_by(email=email).first():
        return err("School slug or admin email already exists", 409)
    school = School(name=name, slug=slug, county=clean(d.get("county")), school_type=d.get("school_type", "primary"))
    db.session.add(school)
    db.session.flush()
    admin = User(school_id=school.id, email=email, first_name=clean(d.get("admin_first_name")) or "School",
                 last_name=clean(d.get("admin_last_name")) or "Admin", role="school_admin")
    admin.set_password(d["admin_password"])
    db.session.add(admin)
    audit("school.created", "school", school.id)
    db.session.commit()
    return ok(school.to_dict(), 201)


@bp.patch("/<int:school_id>/status")
@roles_required("super_admin")
def set_status(school_id):
    s = db.session.get(School, school_id)
    if not s:
        return err("School not found", 404)
    s.is_active = bool((request.get_json(silent=True) or {}).get("is_active"))
    audit("school.status", "school", s.id, {"is_active": s.is_active})
    db.session.commit()
    return ok(s.to_dict())
