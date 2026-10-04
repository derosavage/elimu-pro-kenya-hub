from datetime import datetime

from flask import Blueprint, request, g
from flask_jwt_extended import create_access_token

from ..extensions import db
from ..models import School, User, Student, StudentApplication
from ..services import admissions as adm
from ..utils.responses import ok, err
from ..utils.security import roles_required
from ..utils.validation import clean, normalize_phone, password_problem, valid_email

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _session(user):
    return {"token": create_access_token(identity=str(user.id)), "user": user.to_dict()}


@bp.post("/register")
def register():
    """Student self-signup: creates the account AND a draft admission application."""
    d = request.get_json(silent=True) or {}
    e = {}
    first, last = clean(d.get("first_name")), clean(d.get("last_name"))
    email = (clean(d.get("email")) or "").lower()
    phone = normalize_phone(d.get("phone"))
    if not first:
        e["first_name"] = "First name is required"
    if not last:
        e["last_name"] = "Last name is required"
    if not valid_email(email):
        e["email"] = "Enter a valid email address"
    if not phone:
        e["phone"] = "Enter a valid Kenyan phone number, e.g. 0712 345 678"
    pw = password_problem(d.get("password"))
    if pw:
        e["password"] = pw
    school = db.session.get(School, d.get("school_id")) if isinstance(d.get("school_id"), int) else None
    if not school or not school.is_active:
        e["school_id"] = "Select a school"
    elif not school.admissions_open:
        e["school_id"] = "This school is not accepting applications right now"
    if e:
        return err("Please fix the highlighted fields", 422, e)
    if User.query.filter_by(email=email).first():
        return err("An account with this email already exists", 409, {"email": "Email already registered"})

    user = User(school_id=school.id, email=email, phone=phone, first_name=first,
                middle_name=clean(d.get("middle_name")) or None, last_name=last, role="student")
    user.set_password(d["password"])
    db.session.add(user)
    db.session.flush()
    adm.create_draft(user)
    db.session.commit()
    return ok(_session(user), 201, "Account created")


@bp.post("/login")
def login():
    d = request.get_json(silent=True) or {}
    user = User.query.filter_by(email=(clean(d.get("email")) or "").lower()).first()
    if not user or not isinstance(d.get("password"), str) or not user.check_password(d["password"]):
        return err("Invalid email or password", 401)
    if not user.is_active:
        return err("This account has been deactivated", 403)
    if user.school and not user.school.is_active:
        return err("This school account is deactivated", 403)
    user.last_login = datetime.utcnow()
    db.session.commit()
    return ok(_session(user))


@bp.get("/me")
@roles_required()
def me():
    data = g.user.to_dict()
    if g.user.role == "student":
        s = Student.query.filter_by(user_id=g.user.id).first()
        a = StudentApplication.query.filter_by(applicant_user_id=g.user.id).first()
        data["is_enrolled"] = bool(s)
        data["application_status"] = a.status if a else None
    return ok(data)


@bp.post("/change-password")
@roles_required()
def change_password():
    d = request.get_json(silent=True) or {}
    if not g.user.check_password(d.get("current_password") or ""):
        return err("Current password is incorrect", 422, {"current_password": "Incorrect password"})
    problem = password_problem(d.get("new_password"))
    if problem:
        return err(problem, 422, {"new_password": problem})
    g.user.set_password(d["new_password"])
    db.session.commit()
    return ok(message="Password updated")
