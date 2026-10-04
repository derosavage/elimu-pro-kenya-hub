"""Admission business logic: draft creation, validation, submission, enrolment."""
import secrets
from datetime import date, datetime

from ..extensions import db
from ..models import (SchoolClass, Stream, Student, Guardian, StudentApplication)
from ..utils.validation import clean, normalize_phone, parse_date, valid_email

REQUIRED_TO_SUBMIT = {
    "first_name": "First name", "last_name": "Last name", "date_of_birth": "Date of birth",
    "gender": "Gender", "nationality": "Nationality", "applying_class_id": "Class applying for",
    "guardian_name": "Parent/guardian name", "guardian_relationship": "Relationship",
    "guardian_phone": "Parent/guardian phone", "emergency_contact_name": "Emergency contact name",
    "emergency_contact_phone": "Emergency contact phone",
}
EDITABLE_STATUSES = ("draft", "changes_required")


def create_draft(user):
    app = StudentApplication(school_id=user.school_id, applicant_user_id=user.id,
                             first_name=user.first_name, middle_name=user.middle_name,
                             last_name=user.last_name, status="draft")
    db.session.add(app)
    return app


def apply_updates(application, payload):
    """Validate and apply a partial update. Returns dict of field errors."""
    errors = {}
    for key in StudentApplication.EDITABLE:
        if key not in payload:
            continue
        val = clean(payload[key])
        if val in ("", None):
            setattr(application, key, None)
            continue
        if key == "date_of_birth":
            d = parse_date(val)
            if not d or d >= date.today() or d.year < 1990:
                errors[key] = "Enter a valid date of birth (YYYY-MM-DD)"
                continue
            val = d
        elif key in ("guardian_phone", "emergency_contact_phone"):
            val = normalize_phone(val)
            if not val:
                errors[key] = "Enter a valid Kenyan phone number, e.g. 0712 345 678"
                continue
        elif key == "guardian_email" and not valid_email(val):
            errors[key] = "Enter a valid email address"
            continue
        elif key == "gender" and str(val).lower() not in ("male", "female"):
            errors[key] = "Select Male or Female"
            continue
        elif key == "applying_class_id":
            c = SchoolClass.query.filter_by(id=val if isinstance(val, int) else -1,
                                            school_id=application.school_id).first()
            if not c:
                errors[key] = "Select a valid class"
                continue
        elif isinstance(val, str) and len(val) > 200:
            errors[key] = "Too long"
            continue
        setattr(application, key, val.lower() if key == "gender" else val)
    return errors


def missing_for_submit(application):
    return {k: f"{label} is required" for k, label in REQUIRED_TO_SUBMIT.items()
            if not getattr(application, k)}


def new_reference():
    while True:
        ref = f"ELM-{date.today().year}-{secrets.token_hex(3).upper()}"
        if not StudentApplication.query.filter_by(reference_no=ref).first():
            return ref


def submit(application):
    application.status = "submitted"
    application.submitted_at = datetime.utcnow()
    if not application.reference_no:
        application.reference_no = new_reference()


def next_admission_number(school):
    year = date.today().year
    prefix = (school.admission_prefix or "").strip()
    n = Student.query.filter_by(school_id=school.id).count() + 1
    while True:
        num = f"{prefix}{n:04d}/{year}" if prefix else f"{n:04d}/{year}"
        if not Student.query.filter_by(school_id=school.id, admission_number=num).first():
            return num
        n += 1


def enrol(application, school, reviewer_id, class_id, stream_id=None, admission_number=None):
    """Turn an approved application into a Student record. Returns (student, error)."""
    klass = SchoolClass.query.filter_by(id=class_id, school_id=school.id).first()
    if not klass:
        return None, "Select a valid class"
    stream = None
    if stream_id:
        stream = Stream.query.filter_by(id=stream_id, school_id=school.id, class_id=klass.id).first()
        if not stream:
            return None, "That stream does not belong to the selected class"
    number = clean(admission_number) or next_admission_number(school)
    if Student.query.filter_by(school_id=school.id, admission_number=number).first():
        return None, "That admission number is already in use"

    user = application.applicant
    student = Student(
        school_id=school.id, user_id=user.id, admission_number=number,
        first_name=application.first_name, middle_name=application.middle_name,
        last_name=application.last_name, date_of_birth=application.date_of_birth,
        gender=application.gender, nationality=application.nationality, county=application.county,
        previous_school=application.previous_school, phone=user.phone, email=user.email,
        class_id=klass.id, stream_id=stream.id if stream else None,
        status="active", admitted_on=date.today())
    db.session.add(student)
    db.session.flush()
    db.session.add(Guardian(school_id=school.id, student_id=student.id, full_name=application.guardian_name,
                            relationship_type=application.guardian_relationship,
                            phone=application.guardian_phone, email=application.guardian_email))
    if application.emergency_contact_phone and application.emergency_contact_phone != application.guardian_phone:
        db.session.add(Guardian(school_id=school.id, student_id=student.id,
                                full_name=application.emergency_contact_name,
                                phone=application.emergency_contact_phone, is_emergency_contact=True))
    application.student_id = student.id
    application.status = "enrolled"
    application.reviewed_by = reviewer_id
    application.reviewed_at = datetime.utcnow()
    return student, None
