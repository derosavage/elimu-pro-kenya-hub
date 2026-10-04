from app.extensions import db
from app.models import Student, Guardian, SchoolClass, User
from conftest import login


def mary(client):
    return login(client, "mary.otieno@mwangaza.demo")


def james(client):
    return login(client, "james.mwangi@mwangaza.demo")


def kid(app, name):
    return Student.query.filter_by(school_id=app.ids["school1"], first_name=name).first()


# ---------- dashboard & children ----------
def test_parent_dashboard_shows_all_linked_children(client, app):
    d = client.get("/api/parent/dashboard", headers=mary(client)).get_json()["data"]
    assert d["parent"]["first_name"] == "Mary" and d["school"]["name"] == "Mwangaza Academy"
    kids = {c["first_name"]: c for c in d["children"]}
    assert set(kids) == {"Achieng", "Wekesa"}
    assert kids["Achieng"]["fee_balance"] == 7500 and kids["Achieng"]["latest_result"]["mean_grade"] == "B+"
    assert kids["Wekesa"]["fee_balance"] == 0 and kids["Wekesa"]["class"] == "Grade 4"
    assert d["total_balance"] == 7500
    one = client.get("/api/parent/dashboard", headers=james(client)).get_json()["data"]
    assert [c["first_name"] for c in one["children"]] == ["Baraka"] and one["total_balance"] == 22500


def test_child_results_fees_timetable_overview(client, app):
    h, a = mary(client), kid(app, "Achieng")
    res = client.get(f"/api/parent/children/{a.id}/results", headers=h).get_json()["data"][0]
    assert res["subjects"][0]["subject"] == "Mathematics" and res["subjects"][0]["grade"] == "B+"
    f = client.get(f"/api/parent/children/{a.id}/fees", headers=h).get_json()["data"]
    assert f["total_due"] == 22500 and f["total_paid"] == 15000 and f["payments"][0]["reference"] == "SLK8D2F1QX"
    tt = client.get(f"/api/parent/children/{a.id}/timetable", headers=h).get_json()["data"]
    assert tt["1"][0]["title"] == "Mathematics"
    ov = client.get(f"/api/parent/children/{a.id}", headers=h).get_json()["data"]
    assert ov["admission_number"].startswith("MWA") and ov["guardians"][0]["full_name"] == "Mary Otieno"
    wek = kid(app, "Wekesa")
    r4 = client.get(f"/api/parent/children/{wek.id}/results", headers=h).get_json()["data"][0]
    assert r4["mean_grade"] == "A" and r4["subjects"][0]["marks"] == 88.0


# ---------- isolation ----------
def test_parent_cannot_see_unlinked_or_other_school_children(client, app):
    h = mary(client)
    baraka, other = kid(app, "Baraka"), Student.query.filter_by(school_id=app.ids["school2"]).first()
    for sid in (baraka.id, other.id, 99999):
        for part in ("", "/results", "/fees", "/timetable"):
            assert client.get(f"/api/parent/children/{sid}{part}", headers=h).status_code == 404, (sid, part)


def test_parent_cannot_use_other_roles_endpoints(client, app):
    h = mary(client)
    for url in ("/api/students", "/api/students/1", "/api/admissions", "/api/students/me/dashboard", "/api/teacher/dashboard",
                "/api/teachers", "/api/parents", "/api/fees/balances", "/api/payments", "/api/schools/overview"):
        assert client.get(url, headers=h).status_code in (403, 404), url
    assert client.get("/api/students", headers=h).status_code == 403
    assert client.post("/api/payments", headers=h, json={}).status_code == 403
    assert client.post("/api/results", headers=h, json={}).status_code == 403
    # and other roles cannot use parent endpoints
    assert client.get("/api/parent/dashboard", headers=login(client, "achieng@mwangaza.demo")).status_code == 403
    assert client.get("/api/parent/dashboard", headers=login(client, "admin@mwangaza.demo")).status_code == 403


def test_deactivated_student_still_visible_to_parent_but_deactivated_parent_blocked(client, app):
    p = User.query.filter_by(email="james.mwangi@mwangaza.demo").first()
    h = james(client)
    p.is_active = False
    db.session.commit()
    assert client.get("/api/parent/dashboard", headers=h).status_code == 401
    assert client.post("/api/auth/login", json={"email": p.email, "password": "Demo@1234"}).status_code == 403


# ---------- announcements ----------
def test_parent_announcements_audience_and_class_targeting(client, app):
    titles_m = {a["title"] for a in client.get("/api/parent/announcements", headers=mary(client)).get_json()["data"]}
    titles_j = {a["title"] for a in client.get("/api/parent/announcements", headers=james(client)).get_json()["data"]}
    assert "Parents' meeting" in titles_m and "Term 3 opening and fee deadline" in titles_m
    assert "Grade 4 museum trip" in titles_m          # Mary has a Grade 4 child
    assert "Grade 4 museum trip" not in titles_j      # James only has a Grade 7 child
    assert "Staff briefing" not in titles_m | titles_j


# ---------- admin creates parent accounts ----------
def test_admin_lists_parents_with_children(client, app, admin):
    rows = client.get("/api/parents", headers=admin).get_json()["data"]
    m = [r for r in rows if r["email"] == "mary.otieno@mwangaza.demo"][0]
    assert {c["full_name"] for c in m["children"]} == {"Achieng Otieno", "Wekesa Otieno"}
    assert client.get("/api/parents", headers=login(client, "admin@tumaini.demo")).get_json()["data"] == []


def test_admin_creates_parent_login_for_guardian(client, app, admin2):
    neema = Student.query.filter_by(school_id=app.ids["school2"]).first()
    g = neema.guardians[0]
    assert g.to_dict()["has_account"] is False
    body = {"guardian_id": g.id, "email": "rose.atieno@tumaini.demo", "password": "Rose123456"}
    r = client.post(f"/api/students/{neema.id}/parent-account", headers=admin2, json=body)
    assert r.status_code == 201 and r.get_json()["data"]["new_account"] is True
    h = login(client, "rose.atieno@tumaini.demo", "Rose123456")
    kids = client.get("/api/parent/dashboard", headers=h).get_json()["data"]["children"]
    assert [k["full_name"] for k in kids] == ["Neema Atieno"]
    # a second attempt for the same guardian is refused
    assert client.post(f"/api/students/{neema.id}/parent-account", headers=admin2, json=body).status_code == 409


def test_parent_account_validation(client, app, admin2):
    neema = Student.query.filter_by(school_id=app.ids["school2"]).first()
    gid = neema.guardians[0].id
    url = f"/api/students/{neema.id}/parent-account"
    assert client.post(url, headers=admin2, json={"guardian_id": gid, "email": "bad", "password": "Rose123456"}).status_code == 422
    assert client.post(url, headers=admin2, json={"guardian_id": gid, "email": "x@tumaini.demo", "password": "short"}).status_code == 422
    assert client.post(url, headers=admin2, json={"guardian_id": 99999, "email": "x@tumaini.demo", "password": "Rose123456"}).status_code == 404
    # email used by a non-parent account
    assert client.post(url, headers=admin2, json={"guardian_id": gid, "email": "admin@tumaini.demo", "password": "Rose123456"}).status_code == 409
    # email used by a parent of ANOTHER school
    assert client.post(url, headers=admin2, json={"guardian_id": gid, "email": "mary.otieno@mwangaza.demo", "password": "Rose123456"}).status_code == 409


def test_sibling_is_linked_to_existing_parent_account(client, app, admin):
    wek = kid(app, "Wekesa")
    g = wek.guardians[0]
    g.user_id = None                      # simulate: sibling added without a login yet
    db.session.commit()
    assert len(client.get("/api/parent/dashboard", headers=mary(client)).get_json()["data"]["children"]) == 1
    r = client.post(f"/api/students/{wek.id}/parent-account", headers=admin,
                    json={"guardian_id": g.id, "email": "mary.otieno@mwangaza.demo"})   # no password needed to link
    assert r.status_code == 200 and r.get_json()["data"]["new_account"] is False
    assert len(client.get("/api/parent/dashboard", headers=mary(client)).get_json()["data"]["children"]) == 2


def test_cross_school_and_role_limits_on_parent_account_creation(client, app, admin2):
    wek = kid(app, "Wekesa")
    g = wek.guardians[0]
    body = {"guardian_id": g.id, "email": "spy@tumaini.demo", "password": "Spy1234567"}
    assert client.post(f"/api/students/{wek.id}/parent-account", headers=admin2, json=body).status_code == 404
    assert client.post(f"/api/students/{wek.id}/parent-account", headers=login(client, "teacher@mwangaza.demo"), json=body).status_code == 403
    assert client.post(f"/api/students/{wek.id}/parent-account", headers=mary(client), json=body).status_code == 403
