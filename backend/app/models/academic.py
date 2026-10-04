from ..extensions import db
from .core import now


class SchoolClass(db.Model):
    __tablename__ = "classes"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    name = db.Column(db.String(60), nullable=False)  # e.g. "Grade 4", "Form 2"
    level_order = db.Column(db.Integer, default=0)
    streams = db.relationship("Stream", backref="school_class", cascade="all, delete-orphan")
    __table_args__ = (db.UniqueConstraint("school_id", "name"),)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "level_order": self.level_order,
                "streams": [s.to_dict() for s in self.streams]}


class Stream(db.Model):
    __tablename__ = "streams"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False, index=True)
    name = db.Column(db.String(60), nullable=False)
    __table_args__ = (db.UniqueConstraint("class_id", "name"),)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "class_id": self.class_id}


class Subject(db.Model):
    __tablename__ = "subjects"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20))
    __table_args__ = (db.UniqueConstraint("school_id", "name"),)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "code": self.code}


class GradeBand(db.Model):
    """School-configurable grading: marks >= min_mark earns `grade`."""
    __tablename__ = "grade_bands"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    min_mark = db.Column(db.Numeric(5, 2), nullable=False)
    grade = db.Column(db.String(10), nullable=False)
    remark = db.Column(db.String(80))


def grade_for(school_id, marks):
    bands = (GradeBand.query.filter_by(school_id=school_id)
             .order_by(GradeBand.min_mark.desc()).all())
    for b in bands:
        if float(marks) >= float(b.min_mark):
            return b.grade, b.remark
    return None, None


class Exam(db.Model):
    __tablename__ = "exams"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    term_id = db.Column(db.Integer, db.ForeignKey("terms.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)  # e.g. "Opener", "Mid-Term", "End of Term"
    max_score = db.Column(db.Integer, default=100, nullable=False)
    term = db.relationship("Term")


class ExamResult(db.Model):
    __tablename__ = "exam_results"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    marks = db.Column(db.Numeric(5, 2), nullable=False)
    remark = db.Column(db.String(255))
    exam = db.relationship("Exam")
    subject = db.relationship("Subject")
    __table_args__ = (db.UniqueConstraint("exam_id", "student_id", "subject_id"),)


class TimetableEntry(db.Model):
    __tablename__ = "timetable_entries"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False, index=True)
    stream_id = db.Column(db.Integer, db.ForeignKey("streams.id"))
    day_of_week = db.Column(db.Integer, nullable=False)  # 1=Monday ... 5=Friday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"))
    title = db.Column(db.String(100))  # used for Break, Lunch, Assembly...
    teacher_name = db.Column(db.String(120))
    subject = db.relationship("Subject")

    def to_dict(self):
        return {"id": self.id, "day_of_week": self.day_of_week,
                "start_time": self.start_time.strftime("%H:%M"), "end_time": self.end_time.strftime("%H:%M"),
                "title": self.subject.name if self.subject else self.title, "teacher": self.teacher_name}


class TeacherAssignment(db.Model):
    """A teacher teaches a subject in a class (optionally one stream). Drives all teacher permissions."""
    __tablename__ = "teacher_assignments"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    school_class = db.relationship("SchoolClass")
    subject = db.relationship("Subject")
    __table_args__ = (db.UniqueConstraint("teacher_id", "class_id", "subject_id"),)

    def to_dict(self):
        return {"id": self.id, "class_id": self.class_id, "class": self.school_class.name,
                "subject_id": self.subject_id, "subject": self.subject.name}
