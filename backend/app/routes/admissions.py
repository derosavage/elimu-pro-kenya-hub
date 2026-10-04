from datetime import datetime

from flask import Blueprint, request, g
from sqlalchemy import or_

from ..extensions import db
from ..models import StudentApplication, User
from ..services import admissions as adm
from ..utils.responses import ok, err
from ..utils.security import roles_required, scoped_get, audit, ADMIN_ROLES
from ..utils.validation import paginate

bp = Blueprint("admissions", __name__, url_prefix="/api/admissions")


def _mine():
    return StudentApplication.query.filter_by(applicant_user_id=g.user.id, school_id=g.user.school_id).first()


# ---------- student side ----------
@bp.get("/my")
@roles_required("student")
def my_application():
    a = _mine()
    return ok(a.to_dict(detail=True) if a else None)


@bp.put("/my")
@roles_required("student")
def save_draft():
    a = _mine()
    if not a:
        return err("No application found", 404)
    if a.status not in adm.EDITABLE_STATUSES:
        return err("This application can no longer be edited", 409)
    errors = adm.apply_updates(a, request.get_json(silent=True) or {})
    if errors:
        db.session.rollback()
        return err("Please fix the highlighted fields", 422, errors)
    db.session.commit()
    return ok(a.to_dict(detail=True), message="Draft saved")


@bp.post("/my/submit")
@roles_required("student")
def submit_application():
    a = _mine()
    if not a:
        return err("No application found", 404)
    if a.status not in adm.EDITABLE_STATUSES:
        return err("This application has already been submitted", 409)
    payload = request.get_json(silent=True)
    if payload:
        errors = adm.apply_updates(a, payload)
        if errors:
            db.session.rollback()
            return err("Please fix the highlighted fields", 422, errors)
    missing = adm.missing_for_submit(a)
    if missing:
        db.session.rollback()
        return err("Complete all required fields before submitting", 422, missing)
    adm.submit(a)
    db.session.commit()
    return ok(a.to_dict(detail=True), message=f"Application submitted. Your reference number is {a.reference_no}")


# ---------- admin side ----------
@bp.get("")
@roles_required(*ADMIN_ROLES)
def list_applications():
    q = StudentApplication.query.filter(StudentApplication.school_id == g.user.school_id,
                                        StudentApplication.status != "draft")
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{term}%"
        q = q.filter(or_(StudentApplication.reference_no.like(like), StudentApplication.first_name.like(like),
                         StudentApplication.last_name.like(like)))
    items, meta = paginate(q.order_by(StudentApplication.submitted_at.desc()))
    return ok([a.to_dict() for a in items], meta=meta)


@bp.get("/<int:app_id>")
@roles_required(*ADMIN_ROLES)
def get_application(app_id):
    a = scoped_get(StudentApplication, app_id)
    if not a or a.status == "draft":
        return err("Application not found", 404)
    return ok(a.to_dict(detail=True))


@bp.post("/<int:app_id>/review")
@roles_required(*ADMIN_ROLES)
def review(app_id):
    a = scoped_get(StudentApplication, app_id)
    if not a or a.status == "draft":
        return err("Application not found", 404)
    d = request.get_json(silent=True) or {}
    action, note = d.get("action"), (d.get("note") or "").strip()
    allowed = {"under_review": ("submitted", "changes_required"),
               "changes_required": ("submitted", "under_review"),
               "rejected": ("submitted", "under_review", "changes_required")}
    if action not in allowed:
        return err("Action must be under_review, changes_required or rejected", 422)
    if a.status not in allowed[action]:
        return err(f"Cannot move an application from {a.status} to {action}", 409)
    if action in ("changes_required", "rejected") and not note:
        return err("A note is required so the applicant knows why", 422, {"note": "Note is required"})
    a.status, a.review_note = action, note or None
    a.reviewed_by, a.reviewed_at = g.user.id, datetime.utcnow()
    audit(f"application.{action}", "application", a.id, {"note": note})
    db.session.commit()
    return ok(a.to_dict(detail=True))


@bp.post("/<int:app_id>/approve")
@roles_required(*ADMIN_ROLES)
def approve(app_id):
    a = scoped_get(StudentApplication, app_id)
    if not a or a.status == "draft":
        return err("Application not found", 404)
    if a.status not in ("submitted", "under_review"):
        return err(f"An application that is {a.status} cannot be approved", 409)
    d = request.get_json(silent=True) or {}
    if not d.get("class_id"):
        return err("Assign a class before approving", 422, {"class_id": "Class is required"})
    student, problem = adm.enrol(a, g.user.school, g.user.id, d.get("class_id"),
                                 d.get("stream_id"), d.get("admission_number"))
    if problem:
        db.session.rollback()
        return err(problem, 422)
    a.review_note = (d.get("note") or "").strip() or None
    audit("application.approved", "application", a.id, {"student_id": student.id,
                                                          "admission_number": student.admission_number})
    db.session.commit()
    return ok({"application": a.to_dict(detail=True), "student": student.to_dict()},
              message=f"Approved. Admission number {student.admission_number} assigned.")
