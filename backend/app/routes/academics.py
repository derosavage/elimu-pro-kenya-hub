from flask import Blueprint, request, g

from ..extensions import db
from ..models import (SchoolClass, Stream, Subject, Term, Exam, ExamResult, Student, TimetableEntry, GradeBand,
                      grade_for)
from ..utils.responses import ok, err
from ..utils.security import (roles_required, scoped_get, audit, can_teach, teacher_class_ids,
                              ADMIN_ROLES, TEACHER_ROLES)
from ..utils.validation import clean
from datetime import datetime

bp = Blueprint("academics", __name__, url_prefix="/api")
ANY_SCHOOL_USER = ("student", "parent", "teacher", "class_teacher", "bursar", *ADMIN_ROLES)


@bp.get("/classes")
@roles_required(*ANY_SCHOOL_USER)
def list_classes():
    rows = SchoolClass.query.filter_by(school_id=g.user.school_id).order_by(SchoolClass.level_order).all()
    return ok([c.to_dict() for c in rows])


@bp.post("/classes")
@roles_required(*ADMIN_ROLES)
def create_class():
    d = request.get_json(silent=True) or {}
    name = clean(d.get("name"))
    if not name:
        return err("Class name is required", 422, {"name": "Required"})
    if SchoolClass.query.filter_by(school_id=g.user.school_id, name=name).first():
        return err("That class already exists", 409)
    c = SchoolClass(school_id=g.user.school_id, name=name, level_order=int(d.get("level_order") or 0))
    db.session.add(c)
    audit("class.created", "class", None, {"name": name})
    db.session.commit()
    return ok(c.to_dict(), 201)


@bp.post("/classes/<int:class_id>/streams")
@roles_required(*ADMIN_ROLES)
def create_stream(class_id):
    c = scoped_get(SchoolClass, class_id)
    if not c:
        return err("Class not found", 404)
    name = clean((request.get_json(silent=True) or {}).get("name"))
    if not name:
        return err("Stream name is required", 422, {"name": "Required"})
    if Stream.query.filter_by(class_id=c.id, name=name).first():
        return err("That stream already exists in this class", 409)
    s = Stream(school_id=g.user.school_id, class_id=c.id, name=name)
    db.session.add(s)
    db.session.commit()
    return ok(s.to_dict(), 201)


@bp.get("/subjects")
@roles_required(*ANY_SCHOOL_USER)
def list_subjects():
    return ok([s.to_dict() for s in Subject.query.filter_by(school_id=g.user.school_id).order_by(Subject.name)])


@bp.post("/subjects")
@roles_required(*ADMIN_ROLES)
def create_subject():
    d = request.get_json(silent=True) or {}
    name = clean(d.get("name"))
    if not name:
        return err("Subject name is required", 422, {"name": "Required"})
    if Subject.query.filter_by(school_id=g.user.school_id, name=name).first():
        return err("That subject already exists", 409)
    s = Subject(school_id=g.user.school_id, name=name, code=clean(d.get("code")))
    db.session.add(s)
    db.session.commit()
    return ok(s.to_dict(), 201)


@bp.get("/terms")
@roles_required(*ANY_SCHOOL_USER)
def list_terms():
    return ok([t.to_dict() for t in Term.query.filter_by(school_id=g.user.school_id).order_by(Term.id.desc())])


@bp.get("/grading")
@roles_required(*ANY_SCHOOL_USER)
def grading():
    bands = GradeBand.query.filter_by(school_id=g.user.school_id).order_by(GradeBand.min_mark.desc()).all()
    return ok([{"min_mark": float(b.min_mark), "grade": b.grade, "remark": b.remark} for b in bands])


@bp.get("/exams")
@roles_required(*ADMIN_ROLES, *TEACHER_ROLES)
def list_exams():
    q = Exam.query.filter_by(school_id=g.user.school_id)
    if g.user.role in TEACHER_ROLES:
        q = q.filter(Exam.class_id.in_(teacher_class_ids(g.user) or [-1]))
    if request.args.get("class_id", type=int):
        q = q.filter_by(class_id=request.args.get("class_id", type=int))
    return ok([{"id": e.id, "name": e.name, "class_id": e.class_id, "term": e.term.name,
                "year": e.term.academic_year.name, "max_score": e.max_score} for e in q.order_by(Exam.id.desc())])


@bp.post("/exams")
@roles_required(*ADMIN_ROLES, *TEACHER_ROLES)
def create_exam():
    d = request.get_json(silent=True) or {}
    term = scoped_get(Term, d.get("term_id"))
    klass = scoped_get(SchoolClass, d.get("class_id"))
    try:
        max_score = int(d.get("max_score") or 100)
    except (TypeError, ValueError):
        max_score = 0
    if not term or not klass or not clean(d.get("name")) or not 1 <= max_score <= 1000:
        return err("name, term_id and class_id are required and must belong to your school", 422)
    if not can_teach(g.user, klass.id):
        return err("You are not assigned to that class", 403)
    e = Exam(school_id=g.user.school_id, term_id=term.id, class_id=klass.id, name=clean(d["name"]),
             max_score=max_score)
    db.session.add(e)
    audit("exam.created", "exam", None, {"name": e.name, "class_id": klass.id})
    db.session.commit()
    return ok({"id": e.id, "name": e.name, "class_id": e.class_id, "max_score": e.max_score}, 201)


@bp.get("/results")
@roles_required(*ADMIN_ROLES, *TEACHER_ROLES)
def results_sheet():
    """Mark sheet for one exam + subject: every active student in the exam's class with any saved marks."""
    exam, subject = scoped_get(Exam, request.args.get("exam_id", type=int)), scoped_get(Subject, request.args.get("subject_id", type=int))
    if not exam or not subject:
        return err("Exam or subject not found", 404)
    if not can_teach(g.user, exam.class_id, subject.id):
        return err("You are not assigned to teach this subject in this class", 403)
    saved = {r.student_id: r for r in ExamResult.query.filter_by(exam_id=exam.id, subject_id=subject.id)}
    rows = (Student.query.filter_by(school_id=g.user.school_id, class_id=exam.class_id, status="active")
            .order_by(Student.first_name, Student.last_name).all())
    out = []
    for s in rows:
        r = saved.get(s.id)
        grade = grade_for(g.user.school_id, float(r.marks) / exam.max_score * 100)[0] if r else None
        out.append({"student_id": s.id, "full_name": s.full_name, "admission_number": s.admission_number,
                    "stream": s.stream.name if s.stream else None,
                    "marks": float(r.marks) if r else None, "remark": r.remark if r else None, "grade": grade})
    return ok({"exam": {"id": exam.id, "name": exam.name, "max_score": exam.max_score, "term": exam.term.name},
               "subject": subject.to_dict(), "students": out})


@bp.post("/results")
@roles_required(*ADMIN_ROLES, *TEACHER_ROLES)
def enter_results():
    """Body: {exam_id, subject_id, entries:[{student_id, marks, remark?}]}. Upserts.
    Teachers may only enter marks for subjects/classes assigned to them; students must be in the exam's class."""
    d = request.get_json(silent=True) or {}
    exam, subject = scoped_get(Exam, d.get("exam_id")), scoped_get(Subject, d.get("subject_id"))
    if not exam or not subject:
        return err("Exam or subject not found", 404)
    if not can_teach(g.user, exam.class_id, subject.id):
        return err("You are not assigned to teach this subject in this class", 403)
    entries, errors = d.get("entries") or [], {}
    if not entries:
        return err("No entries supplied", 422)
    seen = set()
    for i, en in enumerate(entries):
        st = scoped_get(Student, en.get("student_id"))
        try:
            marks = float(en.get("marks"))
        except (TypeError, ValueError):
            errors[str(i)] = "Marks must be a number"
            continue
        if not st:
            errors[str(i)] = "Student not found in your school"
        elif st.class_id != exam.class_id:
            errors[str(i)] = f"{st.full_name} is not in this exam's class"
        elif st.id in seen:
            errors[str(i)] = "Duplicate student in the same submission"
        elif not 0 <= marks <= exam.max_score:
            errors[str(i)] = f"Marks must be between 0 and {exam.max_score}"
        else:
            seen.add(st.id)
    if errors:
        return err("Some entries are invalid", 422, errors)
    for en in entries:
        r = ExamResult.query.filter_by(exam_id=exam.id, student_id=en["student_id"], subject_id=subject.id).first()
        if not r:
            r = ExamResult(school_id=g.user.school_id, exam_id=exam.id, student_id=en["student_id"],
                           subject_id=subject.id, marks=0)
            db.session.add(r)
        r.marks, r.remark = float(en["marks"]), clean(en.get("remark"))
    audit("results.entered", "exam", exam.id, {"subject_id": subject.id, "count": len(entries)})
    db.session.commit()
    return ok(message=f"{len(entries)} results saved")


@bp.post("/timetable")
@roles_required(*ADMIN_ROLES)
def add_timetable_entry():
    d = request.get_json(silent=True) or {}
    klass = scoped_get(SchoolClass, d.get("class_id"))
    try:
        start = datetime.strptime(d.get("start_time", ""), "%H:%M").time()
        end = datetime.strptime(d.get("end_time", ""), "%H:%M").time()
    except ValueError:
        return err("start_time and end_time must be HH:MM", 422)
    if not klass or d.get("day_of_week") not in (1, 2, 3, 4, 5, 6, 7) or end <= start:
        return err("Invalid class, day or time range", 422)
    subject = scoped_get(Subject, d["subject_id"]) if d.get("subject_id") else None
    if d.get("subject_id") and not subject:
        return err("Subject not found", 404)
    if d.get("stream_id"):
        if not Stream.query.filter_by(id=d["stream_id"], school_id=g.user.school_id, class_id=klass.id).first():
            return err("Stream not found in this class", 404)
    if not subject and not clean(d.get("title")):
        return err("Provide a subject or a title (e.g. Break)", 422)
    e = TimetableEntry(school_id=g.user.school_id, class_id=klass.id, stream_id=d.get("stream_id"),
                       day_of_week=d["day_of_week"], start_time=start, end_time=end,
                       subject_id=subject.id if subject else None, title=clean(d.get("title")),
                       teacher_name=clean(d.get("teacher_name")))
    db.session.add(e)
    db.session.commit()
    return ok(e.to_dict(), 201)
