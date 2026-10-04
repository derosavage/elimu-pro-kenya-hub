from functools import wraps

from flask import g, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from ..extensions import db
from .responses import err

ADMIN_ROLES = ("school_admin", "principal", "deputy_principal")
TEACHER_ROLES = ("teacher", "class_teacher")


def roles_required(*roles):
    """Verify JWT, load the user from the DB (role and school are never taken
    from the token or request body) and enforce the role. Sets g.user."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **k):
            from ..models import User
            verify_jwt_in_request()
            user = db.session.get(User, int(get_jwt_identity()))
            if not user or not user.is_active:
                return err("Account is inactive or no longer exists", 401)
            if roles and user.role not in roles:
                return err("You do not have permission to do this", 403)
            if user.school_id and not user.school.is_active:
                return err("This school account is deactivated", 403)
            g.user = user
            return fn(*a, **k)
        return wrapper
    return deco


def scoped_get(model, obj_id):
    """Fetch a record only if it belongs to the current user's school.
    Callers answer 404 on None, so other schools' IDs are never revealed."""
    return model.query.filter_by(id=obj_id, school_id=g.user.school_id).first()


def audit(action, entity=None, entity_id=None, details=None):
    from ..models import AuditLog
    u = getattr(g, "user", None)
    db.session.add(AuditLog(
        school_id=u.school_id if u else None, user_id=u.id if u else None,
        action=action, entity=entity, entity_id=entity_id, details=details,
        ip_address=request.remote_addr))


def teacher_class_ids(user):
    from ..models import TeacherAssignment
    return {a.class_id for a in TeacherAssignment.query.filter_by(teacher_id=user.id, school_id=user.school_id)}


def can_teach(user, class_id, subject_id=None):
    """Admins may act on any class in their school; teachers only on classes (and subjects) assigned to them."""
    if user.role in ADMIN_ROLES:
        return True
    from ..models import TeacherAssignment
    q = TeacherAssignment.query.filter_by(teacher_id=user.id, school_id=user.school_id, class_id=class_id)
    if subject_id is not None:
        q = q.filter_by(subject_id=subject_id)
    return q.first() is not None
