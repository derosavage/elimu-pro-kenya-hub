from flask import Blueprint, request, g
from sqlalchemy import or_

from ..extensions import db
from ..models import (User, TeacherAssignment, SchoolClass, Subject, Student, Exam, Announcement, Term)
from ..utils.responses import ok, err
from ..utils.security import roles_required, scoped_get, audit, teacher_class_ids, ADMIN_ROLES, TEACHER_ROLES
from ..utils.validation import clean, normalize_phone, password_problem, valid_email

bp = Blueprint("teachers", __name__, url_prefix="/api")


def _teacher_dict(u):
    rows = TeacherAssignment.query.filter_by(teacher_id=u.id).all()
    return {"id": u.id, "full_name": u.full_name, "first_name": u.first_name, "last_name": u.last_name,
            "email": u.email, "phone": u.phone, "is_active": u.is_active, "role": u.role,
            "assignments": [a.to_dict() for a in rows]}


# ---------------- admin: manage teachers ----------------
@bp.get("/teachers")
@roles_required(*ADMIN_ROLES)
def list_teachers():
    rows = (User.query.filter(User.school_id == g.user.school_id, User.role.in_(TEACHER_ROLES))
            .order_by(User.first_name).all())
    return ok([_teacher_dict(u) for u in rows])


@bp.post("/teachers")
@roles_required(*ADMIN_ROLES)
def create_teacher():
    d = request.get_json(silent=True) or {}
    e = {}
    first, last = clean(d.get("first_name")), clean(d.get("last_name"))
    email = (clean(d.get("email")) or "").lower()
    phone = normalize_phone(d.get("phone")) if d.get("phone") else None
    if not first:
        e["first_name"] = "First name is required"
    if not last:
        e["last_name"] = "Last name is required"
    if not valid_email(email):
        e["email"] = "Enter a valid email address"
    if d.get("phone") and not phone:
        e["phone"] = "Enter a valid Kenyan phone number"
    if password_problem(d.get("password")):
        e["password"] = password_problem(d.get("password"))
    role = d.get("role", "teacher")
    if role not in TEACHER_ROLES:
        e["role"] = "Role must be teacher or class_teacher"
    if e:
        return err("Please fix the highlighted fields", 422, e)
    if User.query.filter_by(email=email).first():
        return err("An account with this email already exists", 409, {"email": "Email already registered"})
    u = User(school_id=g.user.school_id, email=email, phone=phone, first_name=first, last_name=last, role=role)
    u.set_password(d["password"])
    db.session.add(u)
    db.session.flush()
    audit("teacher.created", "user", u.id)
    db.session.commit()
    return ok(_teacher_dict(u), 201)


@bp.patch("/teachers/<int:teacher_id>")
@roles_required(*ADMIN_ROLES)
def update_teacher(teacher_id):
    u = scoped_get(User, teacher_id)
    if not u or u.role not in TEACHER_ROLES:
        return err("Teacher not found", 404)
    d = request.get_json(silent=True) or {}
    if "is_active" in d:
        u.is_active = bool(d["is_active"])
    if d.get("role") in TEACHER_ROLES:
        u.role = d["role"]
    audit("teacher.updated", "user", u.id, {k: d[k] for k in ("is_active", "role") if k in d})
    db.session.commit()
    return ok(_teacher_dict(u))


@bp.post("/teachers/<int:teacher_id>/assignments")
@roles_required(*ADMIN_ROLES)
def add_assignment(teacher_id):
    u = scoped_get(User, teacher_id)
    if not u or u.role not in TEACHER_ROLES:
        return err("Teacher not found", 404)
    d = request.get_json(silent=True) or {}
    klass, subject = scoped_get(SchoolClass, d.get("class_id")), scoped_get(Subject, d.get("subject_id"))
    if not klass or not subject:
        return err("Class or subject not found in your school", 404)
    if TeacherAssignment.query.filter_by(teacher_id=u.id, class_id=klass.id, subject_id=subject.id).first():
        return err("This teacher already teaches that subject in that class", 409)
    a = TeacherAssignment(school_id=g.user.school_id, teacher_id=u.id, class_id=klass.id, subject_id=subject.id)
    db.session.add(a)
    audit("teacher.assigned", "user", u.id, {"class_id": klass.id, "subject_id": subject.id})
    db.session.commit()
    return ok(_teacher_dict(u), 201)


@bp.delete("/teachers/<int:teacher_id>/assignments/<int:assignment_id>")
@roles_required(*ADMIN_ROLES)
def remove_assignment(teacher_id, assignment_id):
    a = TeacherAssignment.query.filter_by(id=assignment_id, teacher_id=teacher_id,
                                          school_id=g.user.school_id).first()
    if not a:
        return err("Assignment not found", 404)
    db.session.delete(a)
    audit("teacher.unassigned", "user", teacher_id, {"assignment_id": assignment_id})
    db.session.commit()
    return ok(message="Assignment removed")


# ---------------- teacher self-service ----------------
def _my_classes():
    """[{class_id, class, streams, student_count, subjects:[{id,name}]}] for the current teacher."""
    by_class = {}
    for a in TeacherAssignment.query.filter_by(teacher_id=g.user.id, school_id=g.user.school_id).all():
        c = by_class.setdefault(a.class_id, {"class_id": a.class_id, "class": a.school_class.name, "subjects": [],
                                             "student_count": Student.query.filter_by(
                                                 school_id=g.user.school_id, class_id=a.class_id,
                                                 status="active").count()})
        c["subjects"].append({"id": a.subject_id, "name": a.subject.name})
    return sorted(by_class.values(), key=lambda c: c["class"])


@bp.get("/teacher/dashboard")
@roles_required(*TEACHER_ROLES)
def teacher_dashboard():
    classes = _my_classes()
    ids = [c["class_id"] for c in classes]
    exams = (Exam.query.filter(Exam.school_id == g.user.school_id, Exam.class_id.in_(ids))
             .order_by(Exam.id.desc()).limit(5).all()) if ids else []
    ann = (Announcement.query.filter(Announcement.school_id == g.user.school_id,
                                     Announcement.audience.in_(("all", "teachers")))
           .order_by(Announcement.created_at.desc()).limit(3).all())
    term = Term.query.filter_by(school_id=g.user.school_id, is_current=True).first()
    return ok({"teacher": {"full_name": g.user.full_name, "first_name": g.user.first_name},
              "school": g.user.school.to_dict(public=True), "term": term.to_dict() if term else None,
              "classes": classes, "total_students": sum(c["student_count"] for c in classes),
              "recent_exams": [{"id": e.id, "name": e.name, "class_id": e.class_id, "term": e.term.name} for e in exams],
              "announcements": [a.to_dict() for a in ann]})


@bp.get("/teacher/classes")
@roles_required(*TEACHER_ROLES)
def teacher_classes():
    return ok(_my_classes())


@bp.get("/teacher/classes/<int:class_id>/students")
@roles_required(*TEACHER_ROLES)
def teacher_roster(class_id):
    if class_id not in teacher_class_ids(g.user):
        return err("You are not assigned to that class", 403)
    rows = (Student.query.filter_by(school_id=g.user.school_id, class_id=class_id, status="active")
            .order_by(Student.first_name, Student.last_name).all())
    return ok([{"id": s.id, "full_name": s.full_name, "admission_number": s.admission_number,
                "stream": s.stream.name if s.stream else None, "gender": s.gender} for s in rows])


@bp.get("/teacher/announcements")
@roles_required(*TEACHER_ROLES)
def teacher_announcements():
    rows = (Announcement.query.filter(Announcement.school_id == g.user.school_id,
                                      Announcement.audience.in_(("all", "teachers")))
            .order_by(Announcement.created_at.desc()).limit(100).all())
    return ok([a.to_dict() for a in rows])
