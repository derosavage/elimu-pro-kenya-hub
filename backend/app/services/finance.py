from sqlalchemy import func

from ..extensions import db
from ..models import StudentFee, Payment, Term


def student_statement(school_id, student_id):
    due_rows = (db.session.query(StudentFee.term_id, func.sum(StudentFee.amount_due))
                .filter_by(school_id=school_id, student_id=student_id).group_by(StudentFee.term_id).all())
    paid_rows = dict(db.session.query(Payment.term_id, func.sum(Payment.amount))
                     .filter_by(school_id=school_id, student_id=student_id, status="confirmed")
                     .group_by(Payment.term_id).all())
    terms = {t.id: t for t in Term.query.filter_by(school_id=school_id).all()}
    due_map = {tid: float(v) for tid, v in due_rows}
    per_term = []
    for tid in sorted(set(due_map) | set(paid_rows)):
        due, paid = due_map.get(tid, 0.0), float(paid_rows.get(tid, 0))
        t = terms.get(tid)
        per_term.append({"term_id": tid, "term": t.name if t else "", "year": t.academic_year.name if t else "",
                         "due": due, "paid": paid, "balance": due - paid})
    total_due = sum(p["due"] for p in per_term)
    total_paid = sum(p["paid"] for p in per_term)
    items = (StudentFee.query.filter_by(school_id=school_id, student_id=student_id)
             .order_by(StudentFee.term_id).all())
    payments = (Payment.query.filter_by(school_id=school_id, student_id=student_id)
                .order_by(Payment.paid_at.desc()).all())
    return {"total_due": total_due, "total_paid": total_paid, "balance": total_due - total_paid,
            "per_term": per_term,
            "items": [{"term": i.term.name, "year": i.term.academic_year.name, "description": i.description,
                       "amount": float(i.amount_due)} for i in items],
            "payments": [p.to_dict() for p in payments]}
