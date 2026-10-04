from datetime import datetime

from flask import Blueprint, request, g
from sqlalchemy import or_

from ..extensions import db
from ..models import FeeStructure, StudentFee, Payment, Student, Term, SchoolClass
from ..services import mpesa
from ..services.finance import student_statement
from ..utils.responses import ok, err
from ..utils.security import roles_required, scoped_get, audit, ADMIN_ROLES
from ..utils.validation import clean, paginate, normalize_phone

bp = Blueprint("finance", __name__, url_prefix="/api")
FIN_ROLES = (*ADMIN_ROLES, "bursar")


@bp.get("/fees/structures")
@roles_required(*FIN_ROLES)
def list_structures():
    rows = FeeStructure.query.filter_by(school_id=g.user.school_id).order_by(FeeStructure.id.desc()).all()
    return ok([{"id": r.id, "name": r.name, "amount": float(r.amount), "term_id": r.term_id,
                "class_id": r.class_id} for r in rows])


@bp.post("/fees/structures")
@roles_required(*FIN_ROLES)
def create_structure():
    d = request.get_json(silent=True) or {}
    term = scoped_get(Term, d.get("term_id"))
    try:
        amount = float(d.get("amount"))
    except (TypeError, ValueError):
        amount = -1
    if not term or not clean(d.get("name")) or amount <= 0:
        return err("name, term_id and a positive amount are required", 422)
    if d.get("class_id") and not scoped_get(SchoolClass, d["class_id"]):
        return err("Class not found", 404)
    f = FeeStructure(school_id=g.user.school_id, term_id=term.id, class_id=d.get("class_id"),
                     name=clean(d["name"]), amount=amount)
    db.session.add(f)
    audit("fee_structure.created", "fee_structure", None, {"name": f.name, "amount": amount})
    db.session.commit()
    return ok({"id": f.id}, 201)


@bp.post("/fees/assign")
@roles_required(*FIN_ROLES)
def assign_fees():
    """Charge every active student the fee structures of `term_id` that apply to their class. Idempotent."""
    term = scoped_get(Term, (request.get_json(silent=True) or {}).get("term_id"))
    if not term:
        return err("Term not found", 404)
    structures = FeeStructure.query.filter_by(school_id=g.user.school_id, term_id=term.id).all()
    created = 0
    for s in Student.query.filter_by(school_id=g.user.school_id, status="active").all():
        for fs in structures:
            if fs.class_id and fs.class_id != s.class_id:
                continue
            if StudentFee.query.filter_by(student_id=s.id, fee_structure_id=fs.id).first():
                continue
            db.session.add(StudentFee(school_id=s.school_id, student_id=s.id, term_id=term.id,
                                      fee_structure_id=fs.id, description=fs.name, amount_due=fs.amount))
            created += 1
    audit("fees.assigned", "term", term.id, {"created": created})
    db.session.commit()
    return ok({"created": created})


@bp.get("/fees/balances")
@roles_required(*FIN_ROLES)
def balances():
    q = Student.query.filter_by(school_id=g.user.school_id, status="active")
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{term}%"
        q = q.filter(or_(Student.first_name.like(like), Student.last_name.like(like),
                         Student.admission_number.like(like)))
    items, meta = paginate(q.order_by(Student.first_name))
    rows = []
    for s in items:
        st = student_statement(s.school_id, s.id)
        rows.append({"student_id": s.id, "name": s.full_name, "admission_number": s.admission_number,
                     "class": s.school_class.name if s.school_class else None,
                     "due": st["total_due"], "paid": st["total_paid"], "balance": st["balance"]})
    return ok(rows, meta=meta)


@bp.get("/payments")
@roles_required(*FIN_ROLES)
def list_payments():
    q = Payment.query.filter_by(school_id=g.user.school_id).order_by(Payment.paid_at.desc())
    items, meta = paginate(q)
    return ok([dict(p.to_dict(), student_id=p.student_id) for p in items], meta=meta)


@bp.post("/payments")
@roles_required(*FIN_ROLES)
def record_payment():
    """Manual recording of cash / bank / M-Pesa receipts by the school."""
    d = request.get_json(silent=True) or {}
    student, term = scoped_get(Student, d.get("student_id")), scoped_get(Term, d.get("term_id"))
    try:
        amount = float(d.get("amount"))
    except (TypeError, ValueError):
        amount = -1
    ref = clean(d.get("reference"))
    if not student or not term:
        return err("Student or term not found", 404)
    if amount <= 0 or d.get("method") not in ("cash", "bank", "mpesa") or not ref:
        return err("A positive amount, method (cash/bank/mpesa) and reference are required", 422)
    if Payment.query.filter_by(school_id=g.user.school_id, reference=ref).first():
        return err("A payment with this reference was already recorded", 409)
    count = Payment.query.filter_by(school_id=g.user.school_id).count() + 1
    p = Payment(school_id=g.user.school_id, student_id=student.id, term_id=term.id, amount=amount,
                method=d["method"], reference=ref, receipt_no=f"RCT-{datetime.utcnow().year}-{count:05d}",
                recorded_by=g.user.id)
    db.session.add(p)
    audit("payment.recorded", "payment", None, {"student_id": student.id, "amount": amount})
    db.session.commit()
    return ok(p.to_dict(), 201)


@bp.post("/payments/mpesa/stk-push")
@roles_required(*FIN_ROLES)
def stk_push():
    if not mpesa.configured():
        return err("M-Pesa is not configured on this server. Set the MPESA_* environment variables.", 503)
    d = request.get_json(silent=True) or {}
    student, phone = scoped_get(Student, d.get("student_id")), normalize_phone(d.get("phone"))
    if not student or not phone or not d.get("amount"):
        return err("student_id, phone and amount are required", 422)
    return ok(mpesa.stk_push(phone, d["amount"], student.admission_number))
