from flask import Blueprint, request, g
from sqlalchemy import or_

from ..extensions import db
from ..models import Announcement, SchoolClass, Student
from ..utils.responses import ok, err
from ..utils.security import roles_required, scoped_get, audit, ADMIN_ROLES
from ..utils.validation import clean

bp = Blueprint("announcements", __name__, url_prefix="/api/announcements")


@bp.get("")
@roles_required(*ADMIN_ROLES, "teacher", "class_teacher", "bursar", "student")
def list_announcements():
    q = Announcement.query.filter_by(school_id=g.user.school_id)
    if g.user.role == "student":
        s = Student.query.filter_by(user_id=g.user.id).first()
        q = q.filter(Announcement.audience.in_(("all", "students")),
                     or_(Announcement.class_id.is_(None), Announcement.class_id == (s.class_id if s else -1)))
    if g.user.role in ("teacher", "class_teacher"):
        q = q.filter(Announcement.audience.in_(("all", "teachers")))
    return ok([a.to_dict() for a in q.order_by(Announcement.created_at.desc()).limit(100)])


@bp.post("")
@roles_required(*ADMIN_ROLES)
def create_announcement():
    d = request.get_json(silent=True) or {}
    title, content = clean(d.get("title")), clean(d.get("content"))
    e = {}
    if not title:
        e["title"] = "Title is required"
    if not content:
        e["content"] = "Content is required"
    if d.get("audience", "all") not in ("all", "students", "parents", "teachers"):
        e["audience"] = "Invalid audience"
    if d.get("priority", "normal") not in ("normal", "important", "urgent"):
        e["priority"] = "Invalid priority"
    if d.get("class_id") and not scoped_get(SchoolClass, d["class_id"]):
        e["class_id"] = "Class not found"
    if e:
        return err("Please fix the highlighted fields", 422, e)
    a = Announcement(school_id=g.user.school_id, author_id=g.user.id, title=title, content=content,
                     audience=d.get("audience", "all"), priority=d.get("priority", "normal"),
                     class_id=d.get("class_id"))
    db.session.add(a)
    audit("announcement.created", "announcement", None, {"title": title})
    db.session.commit()
    return ok(a.to_dict(), 201)
