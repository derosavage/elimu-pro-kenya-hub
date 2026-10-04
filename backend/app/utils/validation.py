import re
from datetime import datetime

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean(v):
    return v.strip() if isinstance(v, str) else v


def valid_email(v):
    return isinstance(v, str) and bool(EMAIL_RE.match(v)) and len(v) <= 255


def normalize_phone(v):
    """07xx / 01xx / 254... / +254... -> +254XXXXXXXXX, else None."""
    if not v or not isinstance(v, str):
        return None
    d = re.sub(r"[\s\-()]", "", v).lstrip("+")
    if d.startswith("0") and len(d) == 10:
        d = "254" + d[1:]
    return "+" + d if re.fullmatch(r"254[17]\d{8}", d) else None


def password_problem(pw):
    if not isinstance(pw, str) or len(pw) < 8:
        return "Password must be at least 8 characters"
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password must contain both letters and numbers"
    return None


def parse_date(v):
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def paginate(query, default_per_page=20, max_per_page=100):
    from flask import request
    page = max(request.args.get("page", 1, type=int), 1)
    per = min(max(request.args.get("per_page", default_per_page, type=int), 1), max_per_page)
    p = query.paginate(page=page, per_page=per, error_out=False)
    return p.items, {"page": p.page, "per_page": per, "total": p.total, "pages": p.pages}
