from app.models import Exam, Subject, Student, SchoolClass, Term, User, TeacherAssignment, ExamResult
from conftest import login


def ids(app):
    s = app.ids["school1"]
    return dict(
        exam=Exam.query.filter_by(school_id=s).first(),
        math=Subject.query.filter_by(school_id=s, name="Mathematics").first(),
        agri=Subject.query.filter_by(school_id=s, name="Agriculture").first(),
        g7=SchoolClass.query.filter_by(school_id=s, name="Grade 7").first(),
        g6=SchoolClass.query.filter_by(school_id=s, name="Grade 6").first(),
        term=Term.query.filter_by(school_id=s, is_current=True).first(),
        achieng=Student.query.filter_by(school_id=s, first_name="Achieng").first(),
        baraka=Student.query.filter_by(school_id=s, first_name="Baraka").first(),
    )


def teacher(client):
    return login(client, "teacher@mwangaza.demo")


# ---------- admin manages teachers ----------
def test_admin_creates_teacher_and_assigns(client, app, admin):
    x = ids(app)
    r = client.post("/api/teachers", headers=admin, json={"first_name": "Faith", "last_name": "Njeri",
                    "email": "faith@mwangaza.demo", "password": "Faith12345", "phone": "0711000222"})
    assert r.status_code == 201
    tid = r.get_json()["data"]["id"]
    assert client.post("/api/teachers", headers=admin, json={"first_name": "F", "last_name": "N",
                       "email": "faith@mwangaza.demo", "password": "Faith12345"}).status_code == 409
    assert client.post("/api/teachers", headers=admin, json={"first_name": "", "email": "bad", "password": "x"}).status_code == 422
    a = client.post(f"/api/teachers/{tid}/assignments", headers=admin, json={"class_id": x["g6"].id, "subject_id": x["agri"].id})
    assert a.status_code == 201 and a.get_json()["data"]["assignments"][0]["subject"] == "Agriculture"
    assert client.post(f"/api/teachers/{tid}/assignments", headers=admin, json={"class_id": x["g6"].id, "subject_id": x["agri"].id}).status_code == 409
    aid = a.get_json()["data"]["assignments"][0]["id"]
    assert client.delete(f"/api/teachers/{tid}/assignments/{aid}", headers=admin).status_code == 200
    assert login(client, "faith@mwangaza.demo", "Faith12345")


def test_teacher_management_is_school_scoped_and_admin_only(client, app, admin, admin2):
    x = ids(app)
    t = User.query.filter_by(email="teacher@mwangaza.demo").first()
    assert client.get("/api/teachers", headers=admin2).get_json()["data"] == []
    assert client.patch(f"/api/teachers/{t.id}", headers=admin2, json={"is_active": False}).status_code == 404
    assert client.post(f"/api/teachers/{t.id}/assignments", headers=admin2,
                       json={"class_id": x["g6"].id, "subject_id": x["agri"].id}).status_code == 404
    # school 2's admin cannot assign school 1's class to its own teacher either
    r = client.post("/api/teachers", headers=admin2, json={"first_name": "Otis", "last_name": "Ade",
                    "email": "otis@tumaini.demo", "password": "Otis123456"})
    tid = r.get_json()["data"]["id"]
    assert client.post(f"/api/teachers/{tid}/assignments", headers=admin2,
                       json={"class_id": x["g7"].id, "subject_id": x["math"].id}).status_code == 404
    th = teacher(client)
    assert client.get("/api/teachers", headers=th).status_code == 403
    assert client.post("/api/teachers", headers=th, json={}).status_code == 403


def test_deactivated_teacher_cannot_login(client, app, admin):
    t = User.query.filter_by(email="teacher@mwangaza.demo").first()
    assert client.patch(f"/api/teachers/{t.id}", headers=admin, json={"is_active": False}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "teacher@mwangaza.demo", "password": "Demo@1234"}).status_code == 403


# ---------- teacher self-service ----------
def test_teacher_dashboard_classes_and_roster(client, app):
    x = ids(app)
    th = teacher(client)
    d = client.get("/api/teacher/dashboard", headers=th).get_json()["data"]
    assert d["teacher"]["first_name"] == "David" and d["total_students"] == 2
    assert d["classes"][0]["class"] == "Grade 7" and {s["name"] for s in d["classes"][0]["subjects"]} == {"Mathematics", "English", "Integrated Science"}
    roster = client.get(f"/api/teacher/classes/{x['g7'].id}/students", headers=th).get_json()["data"]
    assert {s["full_name"] for s in roster} == {"Achieng Otieno", "Baraka Mwangi"}
    assert client.get(f"/api/teacher/classes/{x['g6'].id}/students", headers=th).status_code == 403


def test_teacher_only_sees_own_students(client, app):
    x = ids(app)
    th = teacher(client)
    lst = client.get("/api/students", headers=th).get_json()["data"]
    assert len(lst) == 2 and all(s["class"] == "Grade 7" for s in lst)
    assert client.get(f"/api/students/{x['achieng'].id}", headers=th).status_code == 200
    other = Student.query.filter_by(school_id=app.ids["school2"]).first()
    assert client.get(f"/api/students/{other.id}", headers=th).status_code == 404
    # the fee statement is not exposed to teachers
    assert "fees" not in client.get(f"/api/students/{x['achieng'].id}", headers=th).get_json()["data"]


def test_teacher_cannot_use_admin_endpoints(client, app):
    th = teacher(client)
    for method, url in (("get", "/api/admissions"), ("get", "/api/schools/overview"), ("get", "/api/fees/balances"),
                        ("post", "/api/classes"), ("post", "/api/announcements"), ("get", "/api/payments")):
        assert getattr(client, method)(url, headers=th, json={}).status_code == 403, url


def test_teacher_announcements_filtered(client, app, admin):
    client.post("/api/announcements", headers=admin, json={"title": "Staff meeting", "content": "Fri 3pm", "audience": "teachers"})
    client.post("/api/announcements", headers=admin, json={"title": "Parents day", "content": "Sat", "audience": "parents"})
    titles = {a["title"] for a in client.get("/api/teacher/announcements", headers=teacher(client)).get_json()["data"]}
    assert "Staff meeting" in titles and "Term 3 opening and fee deadline" in titles and "Parents day" not in titles


# ---------- result entry ----------
def test_mark_sheet_and_entry_by_assigned_teacher(client, app):
    x = ids(app)
    th = teacher(client)
    sheet = client.get(f"/api/results?exam_id={x['exam'].id}&subject_id={x['math'].id}", headers=th).get_json()["data"]
    row = {r["full_name"]: r for r in sheet["students"]}
    assert row["Achieng Otieno"]["marks"] == 78.0 and row["Achieng Otieno"]["grade"] == "B+"
    r = client.post("/api/results", headers=th, json={"exam_id": x["exam"].id, "subject_id": x["math"].id, "entries": [
        {"student_id": x["achieng"].id, "marks": 91, "remark": "Outstanding"},
        {"student_id": x["baraka"].id, "marks": 45}]})
    assert r.status_code == 200
    saved = ExamResult.query.filter_by(exam_id=x["exam"].id, subject_id=x["math"].id, student_id=x["achieng"].id).first()
    assert float(saved.marks) == 91.0 and saved.remark == "Outstanding"
    # the student sees the update on their own results page
    st = login(client, "achieng@mwangaza.demo")
    res = client.get("/api/students/me/results", headers=st).get_json()["data"][0]["subjects"]
    maths = [s for s in res if s["subject"] == "Mathematics"][0]
    assert maths["marks"] == 91.0 and maths["grade"] == "A" and maths["remark"] == "Outstanding"


def test_teacher_cannot_enter_unassigned_subject_or_class(client, app):
    x = ids(app)
    th = teacher(client)
    body = {"exam_id": x["exam"].id, "subject_id": x["agri"].id, "entries": [{"student_id": x["achieng"].id, "marks": 50}]}
    assert client.post("/api/results", headers=th, json=body).status_code == 403          # subject not assigned
    assert client.get(f"/api/results?exam_id={x['exam'].id}&subject_id={x['agri'].id}", headers=th).status_code == 403
    g6_exam = client.post("/api/exams", headers=login(client, "admin@mwangaza.demo"),
                          json={"name": "G6 Opener", "term_id": x["term"].id, "class_id": x["g6"].id}).get_json()["data"]
    body = {"exam_id": g6_exam["id"], "subject_id": x["math"].id, "entries": []}
    assert client.post("/api/results", headers=th, json=body).status_code == 403          # class not assigned


def test_result_validation(client, app):
    x = ids(app)
    th = teacher(client)
    base = {"exam_id": x["exam"].id, "subject_id": x["math"].id}
    assert client.post("/api/results", headers=th, json={**base, "entries": [{"student_id": x["achieng"].id, "marks": 101}]}).status_code == 422
    assert client.post("/api/results", headers=th, json={**base, "entries": [{"student_id": x["achieng"].id, "marks": -1}]}).status_code == 422
    assert client.post("/api/results", headers=th, json={**base, "entries": [{"student_id": x["achieng"].id, "marks": "abc"}]}).status_code == 422
    assert client.post("/api/results", headers=th, json={**base, "entries": [
        {"student_id": x["achieng"].id, "marks": 50}, {"student_id": x["achieng"].id, "marks": 60}]}).status_code == 422
    assert client.post("/api/results", headers=th, json={**base, "entries": []}).status_code == 422
    # a student from another class / another school cannot be given marks
    outsider = Student.query.filter_by(school_id=app.ids["school2"]).first()
    r = client.post("/api/results", headers=th, json={**base, "entries": [{"student_id": outsider.id, "marks": 50}]})
    assert r.status_code == 422
    # nothing was half-saved by the failed submissions
    assert float(ExamResult.query.filter_by(exam_id=x["exam"].id, subject_id=x["math"].id, student_id=x["achieng"].id).first().marks) == 78.0


def test_teacher_creates_exam_only_for_assigned_class(client, app):
    x = ids(app)
    th = teacher(client)
    ok_ = client.post("/api/exams", headers=th, json={"name": "Mid-Term", "term_id": x["term"].id, "class_id": x["g7"].id, "max_score": 60})
    assert ok_.status_code == 201 and ok_.get_json()["data"]["max_score"] == 60
    assert client.post("/api/exams", headers=th, json={"name": "X", "term_id": x["term"].id, "class_id": x["g6"].id}).status_code == 403
    listed = client.get("/api/exams", headers=th).get_json()["data"]
    assert listed and all(e["class_id"] == x["g7"].id for e in listed)
    # marks are validated against the exam's own maximum (60)
    body = {"exam_id": ok_.get_json()["data"]["id"], "subject_id": x["math"].id}
    assert client.post("/api/results", headers=th, json={**body, "entries": [{"student_id": x["achieng"].id, "marks": 61}]}).status_code == 422
    assert client.post("/api/results", headers=th, json={**body, "entries": [{"student_id": x["achieng"].id, "marks": 45}]}).status_code == 200


def test_other_school_teacher_cannot_touch_results(client, app, admin2):
    x = ids(app)
    r = client.post("/api/teachers", headers=admin2, json={"first_name": "Otis", "last_name": "Ade", "email": "otis@tumaini.demo", "password": "Otis123456"})
    assert r.status_code == 201
    th2 = login(client, "otis@tumaini.demo", "Otis123456")
    body = {"exam_id": x["exam"].id, "subject_id": x["math"].id, "entries": [{"student_id": x["achieng"].id, "marks": 1}]}
    assert client.post("/api/results", headers=th2, json=body).status_code == 404
    assert client.get(f"/api/results?exam_id={x['exam'].id}&subject_id={x['math'].id}", headers=th2).status_code == 404
    assert client.get("/api/exams", headers=th2).get_json()["data"] == []
