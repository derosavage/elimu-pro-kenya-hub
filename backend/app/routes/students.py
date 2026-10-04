from datetime import datetime, timedelta

from flask import Blueprint, request, g
from sqlalchemy import or_

from ..extensions import db
from ..models import (Student, StudentApplication, Term, ExamResult, Exam, TimetableEntry, Announcement,
                      SchoolClass, Stream, grade_for)
from ..services.finance import student_statement
from ..utils.responses import ok, err
from ..utils.security import roles_required, scoped_get, audit, teacher_class_ids, ADMIN_ROLES, TEACHER_ROLES
from ..utils.validation import paginate, normalize_phone

bp = Blueprint("students", __name__, url_prefix="/api/students")


def _me():
    return Student.query.filter_by(user_id=g.user.id, school_id=g.user.school_id).first()


def _need_student():
    s = _me()
    return (s, None) if s else (None, err("You are not enrolled yet", 404))


def results_for(student):
    rows = (ExamResult.query.filter_by(school_id=student.school_id, student_id=student.id)
            .order_by(ExamResult.exam_id.desc()).all())
    exams = {}
    for r in rows:
        grade, remark = grade_for(student.school_id, float(r.marks) / r.exam.max_score * 100)
        ex = exams.setdefault(r.exam_id, {"exam_id": r.exam_id, "exam": r.exam.name, "term": r.exam.term.name,
                                          "year": r.exam.term.academic_year.name, "subjects": []})
        ex["subjects"].append({"subject": r.subject.name, "marks": float(r.marks), "max": r.exam.max_score,
                               "grade": grade, "remark": r.remark or remark})
    out = []
    for ex in exams.values():
        pct = [s["marks"] / s["max"] * 100 for s in ex["subjects"]]
        mean = sum(pct) / len(pct)
        ex["mean"] = round(mean, 1)
        ex["mean_grade"] = grade_for(student.school_id, mean)[0]
        ex["total"] = sum(s["marks"] for s in ex["subjects"])
        out.append(ex)
    return out


def announcements_for(student, limit=None):
    q = Announcement.query.filter(Announcement.school_id == student.school_id,
                                  Announcement.audience.in_(("all", "students")),
                                  or_(Announcement.class_id.is_(None), Announcement.class_id == student.class_id))
    q = q.order_by(Announcement.created_at.desc())
    return [a.to_dict() for a in (q.limit(limit) if limit else q)]


def timetable_for(student):
    q = TimetableEntry.query.filter_by(school_id=student.school_id, class_id=student.class_id)
    q = q.filter(or_(TimetableEntry.stream_id.is_(None), TimetableEntry.stream_id == student.stream_id))
    days = {}
    for e in q.order_by(TimetableEntry.day_of_week, TimetableEntry.start_time).all():
        days.setdefault(e.day_of_week, []).append(e.to_dict())
    return days


# ---------- student self-service ----------
@bp.get("/me")
@roles_required("student")
def my_profile():
    s, bad = _need_student()
    if bad:
        return bad
    return ok(dict(s.to_dict(), school=g.user.school.to_dict(public=True)))


@bp.patch("/me")
@roles_required("student")
def update_my_profile():
    """Students may edit only their own phone number; everything else is admin-controlled."""
    s, bad = _need_student()
    if bad:
        return bad
    phone = normalize_phone((request.get_json(silent=True) or {}).get("phone"))
    if not phone:
        return err("Enter a valid Kenyan phone number", 422, {"phone": "Invalid phone number"})
    s.phone = g.user.phone = phone
    db.session.commit()
    return ok(s.to_dict())


@bp.get("/me/dashboard")
@roles_required("student")
def my_dashboard():
    s, bad = _need_student()
    if bad:
        return bad
    term = Term.query.filter_by(school_id=s.school_id, is_current=True).first()
    stmt = student_statement(s.school_id, s.id)
    current = next((t for t in stmt["per_term"] if term and t["term_id"] == term.id), None)
    results = results_for(s)
    nairobi = datetime.utcnow() + timedelta(hours=3)
    todays = timetable_for(s).get(nairobi.isoweekday(), [])
    nxt = next((e for e in todays if e["end_time"] > nairobi.strftime("%H:%M")), None)
    return ok({"student": s.to_dict(), "school": g.user.school.to_dict(public=True),
               "term": term.to_dict() if term else None,
               "fee_balance": (current or {"balance": stmt["balance"]})["balance"], "total_balance": stmt["balance"],
               "latest_result": results[0] if results else None, "next_lesson": nxt,
               "announcements": announcements_for(s, 3)})


@bp.get("/me/results")
@roles_required("student")
def my_results():
    s, bad = _need_student()
    return bad or ok(results_for(s))


@bp.get("/me/fees")
@roles_required("student")
def my_fees():
    s, bad = _need_student()
    return bad or ok(student_statement(s.school_id, s.id))


@bp.get("/me/timetable")
@roles_required("student")
def my_timetable():
    s, bad = _need_student()
    return bad or ok(timetable_for(s))


@bp.get("/me/announcements")
@roles_required("student")
def my_announcements():
    s, bad = _need_student()
    return bad or ok(announcements_for(s))


# ---------- admin side ----------
@bp.get("")
@roles_required(*ADMIN_ROLES, "bursar", "teacher", "class_teacher")
def list_students():
    q = Student.query.filter_by(school_id=g.user.school_id)
    if g.user.role in TEACHER_ROLES:  # teachers only see learners in classes assigned to them
        q = q.filter(Student.class_id.in_(teacher_class_ids(g.user) or [-1]))
    if request.args.get("class_id", type=int):
        q = q.filter_by(class_id=request.args.get("class_id", type=int))
    if request.args.get("status"):
        q = q.filter_by(status=request.args["status"])
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{term}%"
        q = q.filter(or_(Student.first_name.like(like), Student.last_name.like(like),
                         Student.admission_number.like(like)))
    items, meta = paginate(q.order_by(Student.first_name, Student.last_name))
    return ok([s.to_dict() for s in items], meta=meta)


@bp.get("/<int:student_id>")
@roles_required(*ADMIN_ROLES, "bursar", "teacher", "class_teacher")
def get_student(student_id):
    s = scoped_get(Student, student_id)
    if not s or (g.user.role in TEACHER_ROLES and s.class_id not in teacher_class_ids(g.user)):
        return err("Student not found", 404)
    data = s.to_dict()
    if g.user.role in ADMIN_ROLES or g.user.role == "bursar":
        data["fees"] = student_statement(s.school_id, s.id)
    if g.user.role != "bursar":
        data["results"] = results_for(s)
    return ok(data)


@bp.patch("/<int:student_id>")
@roles_required(*ADMIN_ROLES)
def update_student(student_id):
    s = scoped_get(Student, student_id)
    if not s:
        return err("Student not found", 404)
    d = request.get_json(silent=True) or {}
    if "class_id" in d:
        c = SchoolClass.query.filter_by(id=d["class_id"], school_id=g.user.school_id).first()
        if not c:
            return err("Invalid class", 422)
        s.class_id, s.stream_id = c.id, None
    if "stream_id" in d and d["stream_id"]:
        st = Stream.query.filter_by(id=d["stream_id"], school_id=g.user.school_id, class_id=s.class_id).first()
        if not st:
            return err("Stream does not belong to the student's class", 422)
        s.stream_id = st.id
    if "status" in d:
        if d["status"] not in ("active", "inactive", "transferred", "graduated"):
            return err("Invalid status", 422)
        s.status = d["status"]
        if s.user and d["status"] != "active":
            s.user.is_active = False
        elif s.user:
            s.user.is_active = True
    audit("student.updated", "student", s.id, {k: d[k] for k in ("class_id", "stream_id", "status") if k in d})
    db.session.commit()
    return ok(s.to_dict())
