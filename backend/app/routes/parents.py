from flask import Blueprint, request, g
from sqlalchemy import or_

from ..extensions import db
from ..models import User, Student, Guardian, Term, Announcement
from ..services.finance import student_statement
from ..utils.responses import ok, err
from ..utils.security import roles_required, scoped_get, audit, ADMIN_ROLES
from ..utils.validation import clean, password_problem, valid_email
from .students import results_for, timetable_for

bp = Blueprint("parents", __name__, url_prefix="/api")


# ---------------- admin: parent accounts ----------------
@bp.get("/parents")
@roles_required(*ADMIN_ROLES)
def list_parents():
    rows = User.query.filter_by(school_id=g.user.school_id, role="parent").order_by(User.first_name).all()
    out = []
    for u in rows:
        kids = (Student.query.join(Guardian, Guardian.student_id == Student.id)
                .filter(Guardian.user_id == u.id, Student.school_id == g.user.school_id).all())
        out.append({"id": u.id, "full_name": u.full_name, "email": u.email, "phone": u.phone, "is_active": u.is_active,
                    "children": [{"id": s.id, "full_name": s.full_name, "class": s.school_class.name if s.school_class else None,
                                  "admission_number": s.admission_number} for s in kids]})
    return ok(out)


@bp.post("/students/<int:student_id>/parent-account")
@roles_required(*ADMIN_ROLES)
def create_parent_account(student_id):
    """Give a guardian of this student a parent login. If the email already belongs to a parent of this
    school the guardian is linked to that account instead (siblings share one login)."""
    student = scoped_get(Student, student_id)
    if not student:
        return err("Student not found", 404)
    d = request.get_json(silent=True) or {}
    guardian = Guardian.query.filter_by(id=d.get("guardian_id"), student_id=student.id,
                                        school_id=g.user.school_id).first()
    if not guardian:
        return err("Guardian not found for this student", 404)
    if guardian.user_id:
        return err("This guardian already has a parent login", 409)
    email = (clean(d.get("email")) or "").lower()
    if not valid_email(email):
        return err("Enter a valid email address", 422, {"email": "Enter a valid email address"})
    existing = User.query.filter_by(email=email).first()
    if existing:
        if existing.role != "parent" or existing.school_id != g.user.school_id:
            return err("That email is already used by another account", 409, {"email": "Email already in use"})
        parent, created = existing, False
    else:
        problem = password_problem(d.get("password"))
        if problem:
            return err(problem, 422, {"password": problem})
        parts = guardian.full_name.split()
        parent = User(school_id=g.user.school_id, email=email, phone=guardian.phone, role="parent",
                      first_name=parts[0], last_name=" ".join(parts[1:]) or parts[0])
        parent.set_password(d["password"])
        db.session.add(parent)
        db.session.flush()
        created = True
    guardian.user_id = parent.id
    audit("parent.linked", "student", student.id, {"parent_id": parent.id, "new_account": created})
    db.session.commit()
    return ok({"parent_id": parent.id, "email": parent.email, "new_account": created}, 201 if created else 200)


# ---------------- parent self-service ----------------
def _children(user):
    return (Student.query.join(Guardian, Guardian.student_id == Student.id)
            .filter(Guardian.user_id == user.id, Guardian.school_id == user.school_id,
                    Student.school_id == user.school_id)
            .order_by(Student.first_name).distinct().all())


def _child(student_id):
    """The student only if the logged-in parent is linked to them; otherwise None (callers return 404)."""
    return next((c for c in _children(g.user) if c.id == student_id), None)


def _announcements(limit=None):
    class_ids = [c.class_id for c in _children(g.user) if c.class_id]
    q = Announcement.query.filter(Announcement.school_id == g.user.school_id,
                                  Announcement.audience.in_(("all", "parents")),
                                  or_(Announcement.class_id.is_(None), Announcement.class_id.in_(class_ids or [-1])))
    q = q.order_by(Announcement.created_at.desc())
    return [a.to_dict() for a in (q.limit(limit) if limit else q.limit(100))]


@bp.get("/parent/dashboard")
@roles_required("parent")
def parent_dashboard():
    term = Term.query.filter_by(school_id=g.user.school_id, is_current=True).first()
    kids = []
    for c in _children(g.user):
        stmt = student_statement(c.school_id, c.id)
        cur = next((t for t in stmt["per_term"] if term and t["term_id"] == term.id), None)
        res = results_for(c)
        kids.append({"id": c.id, "full_name": c.full_name, "first_name": c.first_name, "admission_number": c.admission_number,
                     "class": c.school_class.name if c.school_class else None, "stream": c.stream.name if c.stream else None,
                     "status": c.status, "fee_balance": (cur or {"balance": stmt["balance"]})["balance"],
                     "total_balance": stmt["balance"],
                     "latest_result": {"exam": res[0]["exam"], "mean": res[0]["mean"], "mean_grade": res[0]["mean_grade"]} if res else None})
    return ok({"parent": {"full_name": g.user.full_name, "first_name": g.user.first_name},
               "school": g.user.school.to_dict(public=True), "term": term.to_dict() if term else None,
               "children": kids, "total_balance": sum(k["fee_balance"] for k in kids),
               "announcements": _announcements(3)})


@bp.get("/parent/children/<int:student_id>")
@roles_required("parent")
def child_overview(student_id):
    c = _child(student_id)
    if not c:
        return err("Child not found", 404)
    return ok(c.to_dict())


@bp.get("/parent/children/<int:student_id>/results")
@roles_required("parent")
def child_results(student_id):
    c = _child(student_id)
    return ok(results_for(c)) if c else err("Child not found", 404)


@bp.get("/parent/children/<int:student_id>/fees")
@roles_required("parent")
def child_fees(student_id):
    c = _child(student_id)
    return ok(student_statement(c.school_id, c.id)) if c else err("Child not found", 404)


@bp.get("/parent/children/<int:student_id>/timetable")
@roles_required("parent")
def child_timetable(student_id):
    c = _child(student_id)
    return ok(timetable_for(c)) if c else err("Child not found", 404)


@bp.get("/parent/announcements")
@roles_required("parent")
def parent_announcements():
    return ok(_announcements())
