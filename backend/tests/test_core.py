from app.extensions import db
from app.models import User, Student, StudentApplication, School
from conftest import login


def signup(client, school_id, email="newlearner@example.com", **over):
    body = {"school_id": school_id, "first_name": "Wafula", "last_name": "Barasa", "email": email,
            "phone": "0712345678", "password": "Learner123"}
    body.update(over)
    return client.post("/api/auth/register", json=body)


COMPLETE = {"date_of_birth": "2013-03-02", "gender": "male", "nationality": "Kenyan", "county": "Bungoma",
            "guardian_name": "Jane Barasa", "guardian_relationship": "Mother", "guardian_phone": "0722111222",
            "emergency_contact_name": "Jane Barasa", "emergency_contact_phone": "0722111222"}


# ---------------- authentication ----------------
def test_signup_creates_student_and_draft(client, app):
    r = signup(client, app.ids["school1"])
    assert r.status_code == 201
    hdr = {"Authorization": "Bearer " + r.get_json()["data"]["token"]}
    a = client.get("/api/admissions/my", headers=hdr).get_json()["data"]
    assert a["status"] == "draft" and a["reference_no"] is None


def test_signup_validation_and_duplicates(client, app):
    assert signup(client, app.ids["school1"], email="bad", phone="123", password="short").status_code == 422
    assert signup(client, app.ids["school1"]).status_code == 201
    assert signup(client, app.ids["school1"]).status_code == 409


def test_password_is_hashed(client, app):
    signup(client, app.ids["school1"])
    u = User.query.filter_by(email="newlearner@example.com").first()
    assert u.password_hash != "Learner123" and u.password_hash.startswith("$2")


def test_login_and_invalid_credentials(client, app):
    assert client.post("/api/auth/login", json={"email": "admin@mwangaza.demo", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "nobody@x.com", "password": "Demo@1234"}).status_code == 401
    assert login(client, "achieng@mwangaza.demo")


def test_protected_routes_need_token(client):
    assert client.get("/api/students/me").status_code == 401
    assert client.get("/api/admissions").status_code == 401
    assert client.get("/api/students/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_role_restrictions(client, student, admin):
    assert client.get("/api/admissions", headers=student).status_code == 403
    assert client.get("/api/students", headers=student).status_code == 403
    assert client.post("/api/classes", json={"name": "X"}, headers=student).status_code == 403
    assert client.get("/api/students/me", headers=admin).status_code == 403
    assert client.get("/api/schools", headers=admin).status_code == 403  # super admin only


# ---------------- admissions workflow ----------------
def test_submission_validation(client, app):
    hdr = {"Authorization": "Bearer " + signup(client, app.ids["school1"]).get_json()["data"]["token"]}
    r = client.post("/api/admissions/my/submit", headers=hdr)
    assert r.status_code == 422 and "guardian_name" in r.get_json()["errors"]
    r = client.put("/api/admissions/my", json={"guardian_phone": "abc"}, headers=hdr)
    assert r.status_code == 422


def _submitted(client, app):
    hdr = {"Authorization": "Bearer " + signup(client, app.ids["school1"]).get_json()["data"]["token"]}
    from app.models import SchoolClass
    cid = SchoolClass.query.filter_by(school_id=app.ids["school1"], name="Grade 6").first().id
    r = client.post("/api/admissions/my/submit", json=dict(COMPLETE, applying_class_id=cid), headers=hdr)
    assert r.status_code == 200, r.get_json()
    return hdr, r.get_json()["data"]


def test_full_flow_signup_to_dashboard(client, app, admin):
    hdr, sub = _submitted(client, app)
    assert sub["status"] == "submitted" and sub["reference_no"].startswith("ELM-")
    listed = client.get("/api/admissions?status=submitted", headers=admin).get_json()["data"]
    assert any(a["id"] == sub["id"] for a in listed)
    # can't edit after submission
    assert client.put("/api/admissions/my", json={"county": "X"}, headers=hdr).status_code == 409
    # student not enrolled yet
    assert client.get("/api/students/me/dashboard", headers=hdr).status_code == 404

    assert client.post(f"/api/admissions/{sub['id']}/review", json={"action": "under_review"}, headers=admin).status_code == 200
    from app.models import SchoolClass, Stream
    g7 = SchoolClass.query.filter_by(school_id=app.ids["school1"], name="Grade 7").first()
    stream = Stream.query.filter_by(class_id=g7.id, name="West").first()
    assert client.post(f"/api/admissions/{sub['id']}/approve", json={}, headers=admin).status_code == 422  # class required
    r = client.post(f"/api/admissions/{sub['id']}/approve", json={"class_id": g7.id, "stream_id": stream.id}, headers=admin)
    assert r.status_code == 200, r.get_json()
    st = r.get_json()["data"]["student"]
    assert st["admission_number"].startswith("MWA") and st["class"] == "Grade 7" and st["stream"] == "West"
    assert r.get_json()["data"]["application"]["status"] == "enrolled"
    assert len(st["guardians"]) == 1
    # the same login now yields a personalised dashboard
    d = client.get("/api/students/me/dashboard", headers=hdr).get_json()["data"]
    assert d["student"]["admission_number"] == st["admission_number"]
    assert d["school"]["name"] == "Mwangaza Academy"
    assert client.get("/api/auth/me", headers=hdr).get_json()["data"]["is_enrolled"] is True


def test_reject_and_request_changes(client, app, admin):
    hdr, sub = _submitted(client, app)
    r = client.post(f"/api/admissions/{sub['id']}/review", json={"action": "changes_required"}, headers=admin)
    assert r.status_code == 422  # note required
    r = client.post(f"/api/admissions/{sub['id']}/review",
                    json={"action": "changes_required", "note": "Add previous school"}, headers=admin)
    assert r.status_code == 200
    mine = client.get("/api/admissions/my", headers=hdr).get_json()["data"]
    assert mine["status"] == "changes_required" and mine["review_note"] == "Add previous school"
    # applicant can edit and resubmit
    assert client.put("/api/admissions/my", json={"previous_school": "Jua Kali Primary"}, headers=hdr).status_code == 200
    assert client.post("/api/admissions/my/submit", headers=hdr).get_json()["data"]["status"] == "submitted"
    r = client.post(f"/api/admissions/{sub['id']}/review", json={"action": "rejected", "note": "No space"}, headers=admin)
    assert r.get_json()["data"]["status"] == "rejected"
    assert client.post(f"/api/admissions/{sub['id']}/approve", json={"class_id": 1}, headers=admin).status_code == 409


def test_duplicate_admission_number_rejected(client, app, admin):
    _, sub = _submitted(client, app)
    from app.models import SchoolClass
    c = SchoolClass.query.filter_by(school_id=app.ids["school1"], name="Grade 6").first()
    existing = Student.query.filter_by(school_id=app.ids["school1"]).first().admission_number
    r = client.post(f"/api/admissions/{sub['id']}/approve",
                    json={"class_id": c.id, "admission_number": existing}, headers=admin)
    assert r.status_code == 422


# ---------------- multi-tenancy ----------------
def test_school_cannot_read_other_schools_data(client, app, admin, admin2):
    s1_student = Student.query.filter_by(school_id=app.ids["school1"]).first()
    s1_app = StudentApplication.query.filter_by(school_id=app.ids["school1"]).filter(
        StudentApplication.status == "submitted").first()
    assert client.get(f"/api/students/{s1_student.id}", headers=admin).status_code == 200
    assert client.get(f"/api/students/{s1_student.id}", headers=admin2).status_code == 404
    assert client.get(f"/api/admissions/{s1_app.id}", headers=admin2).status_code == 404
    listed = client.get("/api/students", headers=admin2).get_json()["data"]
    assert all(s["id"] != s1_student.id for s in listed) and len(listed) == 1
    assert all(a["id"] != s1_app.id for a in client.get("/api/admissions", headers=admin2).get_json()["data"])


def test_school_cannot_touch_other_schools_finance_or_records(client, app, admin, admin2):
    s1_student = Student.query.filter_by(school_id=app.ids["school1"]).first()
    from app.models import Term, SchoolClass, Stream
    t1 = Term.query.filter_by(school_id=app.ids["school1"], is_current=True).first()
    c1 = SchoolClass.query.filter_by(school_id=app.ids["school1"], name="Grade 7").first()
    # cannot record a payment against another school's student
    r = client.post("/api/payments", headers=admin2, json={"student_id": s1_student.id, "term_id": t1.id,
                                                           "amount": 100, "method": "cash", "reference": "X1"})
    assert r.status_code == 404
    assert all(b["student_id"] != s1_student.id for b in client.get("/api/fees/balances", headers=admin2).get_json()["data"])
    assert client.get("/api/payments", headers=admin2).get_json()["data"] == []
    # cannot modify another school's student / class / approve their applications
    assert client.patch(f"/api/students/{s1_student.id}", json={"status": "inactive"}, headers=admin2).status_code == 404
    assert client.post(f"/api/classes/{c1.id}/streams", json={"name": "Hack"}, headers=admin2).status_code == 404
    s1_app = StudentApplication.query.filter_by(school_id=app.ids["school1"], status="submitted").first()
    c2 = SchoolClass.query.filter_by(school_id=app.ids["school2"], name="Grade 7").first()
    assert client.post(f"/api/admissions/{s1_app.id}/approve", json={"class_id": c2.id}, headers=admin2).status_code == 404
    # cannot enrol into another school's class
    r = client.post(f"/api/admissions/{s1_app.id}/approve", json={"class_id": c2.id}, headers=admin)
    assert r.status_code == 422
    assert db.session.get(Student, s1_student.id).status == "active"


def test_deactivated_school_blocked(client, app):
    s = db.session.get(School, app.ids["school2"])
    hdr = login(client, "admin@tumaini.demo")
    s.is_active = False
    db.session.commit()
    assert client.get("/api/students", headers=hdr).status_code == 403
    assert client.post("/api/auth/login", json={"email": "admin@tumaini.demo", "password": "Demo@1234"}).status_code == 403


# ---------------- student self-service ----------------
def test_student_dashboard_profile_results_fees_timetable_announcements(client, student):
    d = client.get("/api/students/me/dashboard", headers=student).get_json()["data"]
    assert d["student"]["full_name"] == "Achieng Otieno" and d["student"]["class"] == "Grade 7"
    assert d["fee_balance"] == 7500 and d["latest_result"]["mean_grade"] == "B+"
    assert d["announcements"][0]["title"].startswith("Term 3")
    p = client.get("/api/students/me", headers=student).get_json()["data"]
    assert p["admission_number"].startswith("MWA") and p["school"]["name"] == "Mwangaza Academy"
    res = client.get("/api/students/me/results", headers=student).get_json()["data"][0]
    assert {"subject": "Mathematics", "marks": 78.0, "max": 100, "grade": "B+", "remark": "Very good"} == res["subjects"][0]
    f = client.get("/api/students/me/fees", headers=student).get_json()["data"]
    assert f["total_due"] == 22500 and f["total_paid"] == 15000 and f["payments"][0]["receipt_no"] == "RCT-2026-00001"
    tt = client.get("/api/students/me/timetable", headers=student).get_json()["data"]
    assert tt["1"][0]["title"] == "Mathematics" and tt["1"][2]["title"] == "Break"
    assert len(client.get("/api/students/me/announcements", headers=student).get_json()["data"]) == 1


def test_student_can_only_edit_phone(client, student):
    r = client.patch("/api/students/me", json={"phone": "0799000111", "class_id": 999, "admission_number": "HACK"}, headers=student)
    assert r.status_code == 200
    d = r.get_json()["data"]
    assert d["phone"] == "+254799000111" and d["admission_number"].startswith("MWA")


# ---------------- admin management ----------------
def test_admin_class_stream_subject_management(client, admin):
    assert client.post("/api/classes", json={"name": "Form 1"}, headers=admin).status_code == 201
    assert client.post("/api/classes", json={"name": "Form 1"}, headers=admin).status_code == 409
    cid = [c for c in client.get("/api/classes", headers=admin).get_json()["data"] if c["name"] == "Form 1"][0]["id"]
    assert client.post(f"/api/classes/{cid}/streams", json={"name": "North"}, headers=admin).status_code == 201
    assert client.post("/api/subjects", json={"name": "Physics"}, headers=admin).status_code == 201
    assert client.post("/api/subjects", json={"name": ""}, headers=admin).status_code == 422


def test_admin_student_management_and_overview(client, app, admin):
    lst = client.get("/api/students?q=Achieng", headers=admin).get_json()
    assert lst["meta"]["total"] == 1
    sid = lst["data"][0]["id"]
    detail = client.get(f"/api/students/{sid}", headers=admin).get_json()["data"]
    assert detail["fees"]["balance"] == 7500 and len(detail["results"]) == 1
    assert client.patch(f"/api/students/{sid}", json={"status": "transferred"}, headers=admin).status_code == 200
    # transferred student's login is disabled
    assert client.post("/api/auth/login", json={"email": "achieng@mwangaza.demo", "password": "Demo@1234"}).status_code == 403
    o = client.get("/api/schools/overview", headers=admin).get_json()["data"]
    assert o["total_students"] == 3 and o["pending_applications"] == 3 and o["new_applications"] == 2 and o["is_demo"] is True


def test_results_entry_fees_payment_and_announcements(client, app, admin):
    from app.models import Exam, Subject, Student, Term
    ex, sub = Exam.query.first(), Subject.query.filter_by(school_id=app.ids["school1"], name="Agriculture").first()
    stu = Student.query.filter_by(school_id=app.ids["school1"], first_name="Baraka").first()
    assert client.post("/api/results", headers=admin, json={"exam_id": ex.id, "subject_id": sub.id,
        "entries": [{"student_id": stu.id, "marks": 101}]}).status_code == 422
    assert client.post("/api/results", headers=admin, json={"exam_id": ex.id, "subject_id": sub.id,
        "entries": [{"student_id": stu.id, "marks": 90}]}).status_code == 200
    t3 = Term.query.filter_by(school_id=app.ids["school1"], is_current=True).first()
    pay = {"student_id": stu.id, "term_id": t3.id, "amount": 5000, "method": "cash", "reference": "CASH-1"}
    assert client.post("/api/payments", json=pay, headers=admin).status_code == 201
    assert client.post("/api/payments", json=pay, headers=admin).status_code == 409  # duplicate reference
    bal = [b for b in client.get("/api/fees/balances", headers=admin).get_json()["data"] if b["student_id"] == stu.id][0]
    assert bal["balance"] == 17500
    a = client.post("/api/announcements", headers=admin, json={"title": "Sports day", "content": "Friday", "priority": "urgent"})
    assert a.status_code == 201
    assert client.post("/api/announcements", headers=admin, json={"title": "", "content": ""}).status_code == 422


def test_mpesa_reports_not_configured(client, admin):
    r = client.post("/api/payments/mpesa/stk-push", json={}, headers=admin)
    assert r.status_code == 503


def test_super_admin_can_create_school(client):
    hdr = login(client, "super@elimupro.demo")
    r = client.post("/api/schools", headers=hdr, json={"name": "Upendo Primary", "slug": "upendo",
        "admin_email": "head@upendo.demo", "admin_password": "Upendo1234"})
    assert r.status_code == 201
    assert login(client, "head@upendo.demo", "Upendo1234")
    assert len(client.get("/api/schools", headers=hdr).get_json()["data"]) == 3
