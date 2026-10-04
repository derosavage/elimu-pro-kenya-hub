from ..extensions import db
from .core import now


class FeeStructure(db.Model):
    __tablename__ = "fee_structures"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    term_id = db.Column(db.Integer, db.ForeignKey("terms.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"))  # NULL = applies to all classes
    name = db.Column(db.String(120), nullable=False)  # e.g. "Tuition", "Lunch", "Activity"
    amount = db.Column(db.Numeric(12, 2), nullable=False)


class StudentFee(db.Model):
    __tablename__ = "student_fees"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    term_id = db.Column(db.Integer, db.ForeignKey("terms.id"), nullable=False)
    fee_structure_id = db.Column(db.Integer, db.ForeignKey("fee_structures.id"))
    description = db.Column(db.String(120), nullable=False)
    amount_due = db.Column(db.Numeric(12, 2), nullable=False)
    term = db.relationship("Term")


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    term_id = db.Column(db.Integer, db.ForeignKey("terms.id"), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    method = db.Column(db.String(20), nullable=False)  # cash | bank | mpesa
    reference = db.Column(db.String(60), nullable=False)  # bank slip / M-Pesa receipt
    receipt_no = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), default="confirmed", nullable=False)
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    paid_at = db.Column(db.DateTime, default=now, nullable=False)
    term = db.relationship("Term")
    __table_args__ = (db.UniqueConstraint("school_id", "reference"), db.UniqueConstraint("school_id", "receipt_no"))

    def to_dict(self):
        return {"id": self.id, "amount": float(self.amount), "method": self.method, "reference": self.reference,
                "receipt_no": self.receipt_no, "term": self.term.name, "year": self.term.academic_year.name,
                "paid_at": self.paid_at.isoformat()}


class Announcement(db.Model):
    __tablename__ = "announcements"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(10), default="normal", nullable=False)  # normal | important | urgent
    audience = db.Column(db.String(20), default="all", nullable=False)  # all | students | parents | teachers
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"))  # optional class targeting
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    author = db.relationship("User")

    def to_dict(self):
        return {"id": self.id, "title": self.title, "content": self.content, "priority": self.priority,
                "audience": self.audience, "class_id": self.class_id, "author": self.author.full_name,
                "created_at": self.created_at.isoformat()}
