"""DEMO DATA ONLY. Never run against a production database.

Creates two demo schools (so multi-tenant isolation can be seen) and sample
users. All demo accounts use the password in DEMO_PASSWORD.
"""
from datetime import date, time

from .extensions import db
from .models import (School, User, AcademicYear, Term, SchoolClass, Stream, Subject, GradeBand, Exam, ExamResult,
                     Student, Guardian, StudentApplication, FeeStructure, StudentFee, Payment, Announcement,
                     TimetableEntry, TeacherAssignment)
from .services import admissions as adm
from .models import Guardian as _Guardian  # noqa: E402

DEMO_PASSWORD = "Demo@1234"


def _user(school, email, first, last, role, phone=None):
    u = User(school_id=school.id if school else None, email=email, first_name=first, last_name=last,
             role=role, phone=phone)
    u.set_password(DEMO_PASSWORD)
    db.session.add(u)
    db.session.flush()
    return u


def _school(name, slug, county, prefix, stype):
    s = School(name=name, slug=slug, county=county, school_type=stype, admission_prefix=prefix, is_demo=True,
               motto="Learning for life", address=f"{county}, Kenya")
    db.session.add(s)
    db.session.flush()
    y = AcademicYear(school_id=s.id, name="2026", is_current=True)
    db.session.add(y)
    db.session.flush()
    terms = [Term(school_id=s.id, academic_year_id=y.id, name=f"Term {i}", is_current=(i == 3),
                  start_date=d1, end_date=d2) for i, (d1, d2) in enumerate(
        [(date(2026, 1, 5), date(2026, 4, 3)), (date(2026, 4, 27), date(2026, 8, 7)),
         (date(2026, 8, 31), date(2026, 10, 30))], 1)]
    db.session.add_all(terms)
    classes = {}
    for i, n in enumerate(["Grade 4", "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9"], 4):
        c = SchoolClass(school_id=s.id, name=n, level_order=i)
        db.session.add(c)
        classes[n] = c
    db.session.flush()
    for n in ("Grade 7", "Grade 8"):
        for st in ("East", "West"):
            db.session.add(Stream(school_id=s.id, class_id=classes[n].id, name=st))
    subjects = {n: Subject(school_id=s.id, name=n) for n in
                ["Mathematics", "English", "Kiswahili", "Integrated Science", "Social Studies", "Agriculture"]}
    db.session.add_all(subjects.values())
    for m, g, r in [(80, "A", "Excellent"), (70, "B+", "Very good"), (60, "B", "Good"), (50, "C+", "Fair"),
                    (40, "C", "Average"), (0, "D", "Needs improvement")]:
        db.session.add(GradeBand(school_id=s.id, min_mark=m, grade=g, remark=r))
    db.session.flush()
    return s, terms, classes, subjects


def _enrol(school, email, first, last, klass, stream, guardian, phone, gphone="0722000111", dob="2012-05-14", gender="female"):
    u = _user(school, email, first, last, "student", phone)
    a = adm.create_draft(u)
    db.session.flush()
    adm.apply_updates(a, {"date_of_birth": dob, "gender": gender, "nationality": "Kenyan",
                          "applying_class_id": klass.id, "guardian_name": guardian,
                          "guardian_relationship": "Mother", "guardian_phone": gphone,
                          "emergency_contact_name": guardian, "emergency_contact_phone": gphone})
    adm.submit(a)
    st, _ = adm.enrol(a, school, None, klass.id, stream.id if stream else None)
    return st


def seed_demo():
    s1, terms1, cls1, subj1 = _school("Mwangaza Academy", "mwangaza", "Nairobi", "MWA", "mixed")
    admin1 = _user(s1, "admin@mwangaza.demo", "Grace", "Wambui", "school_admin")
    _user(s1, "bursar@mwangaza.demo", "Peter", "Mutua", "bursar")
    _user(None, "super@elimupro.demo", "Platform", "Admin", "super_admin")

    teacher = _user(s1, "teacher@mwangaza.demo", "David", "Kiptoo", "teacher", "0722909090")
    for sub in ("Mathematics", "English", "Integrated Science"):
        db.session.add(TeacherAssignment(school_id=s1.id, teacher_id=teacher.id, class_id=cls1["Grade 7"].id,
                                         subject_id=subj1[sub].id))
    east = Stream.query.filter_by(class_id=cls1["Grade 7"].id, name="East").first()
    achieng = _enrol(s1, "achieng@mwangaza.demo", "Achieng", "Otieno", cls1["Grade 7"], east,
                     "Mary Otieno", "0711223344", gphone="0711556677")
    baraka = _enrol(s1, "baraka@mwangaza.demo", "Baraka", "Mwangi", cls1["Grade 7"], east,
                    "James Mwangi", "0700112233", gphone="0700112299", dob="2012-08-21", gender="male")
    wekesa = _enrol(s1, "wekesa@mwangaza.demo", "Wekesa", "Otieno", cls1["Grade 4"], None,
                    "Mary Otieno", "0711223355", gphone="0711556677", dob="2016-09-03", gender="male")

    # Parent logins. Mary has TWO children (Achieng, Wekesa) on one account, which demonstrates sibling linking.
    mary = _user(s1, "mary.otieno@mwangaza.demo", "Mary", "Otieno", "parent", "0711556677")
    james = _user(s1, "james.mwangi@mwangaza.demo", "James", "Mwangi", "parent", "0700112299")
    for parent, kids in ((mary, (achieng, wekesa)), (james, (baraka,))):
        for kid in kids:
            _Guardian.query.filter_by(student_id=kid.id, is_emergency_contact=False).first().user_id = parent.id

    # Pending applications for the admin to review
    for i, (f, l) in enumerate([("Kiprono", "Koech"), ("Wanjiru", "Kamau"), ("Zawadi", "Chebet")]):
        u = _user(s1, f"{f.lower()}@mwangaza.demo", f, l, "student", f"0733000{i}00"[:10])
        a = adm.create_draft(u)
        db.session.flush()
        adm.apply_updates(a, {"date_of_birth": "2013-02-20", "gender": "male" if i == 0 else "female",
                              "nationality": "Kenyan", "county": "Nakuru", "applying_class_id": cls1["Grade 6"].id,
                              "guardian_name": f"Parent of {f}", "guardian_relationship": "Father",
                              "guardian_phone": "0722555666", "emergency_contact_name": "Aunt",
                              "emergency_contact_phone": "0722777888"})
        adm.submit(a)
        if f == "Zawadi":
            a.status = "under_review"

    # Fees
    t3 = terms1[2]
    tuition = FeeStructure(school_id=s1.id, term_id=t3.id, class_id=None, name="Tuition", amount=18000)
    lunch = FeeStructure(school_id=s1.id, term_id=t3.id, class_id=None, name="Lunch programme", amount=4500)
    db.session.add_all([tuition, lunch])
    db.session.flush()
    for st in (achieng, baraka, wekesa):
        for fs in (tuition, lunch):
            db.session.add(StudentFee(school_id=s1.id, student_id=st.id, term_id=t3.id, fee_structure_id=fs.id,
                                      description=fs.name, amount_due=fs.amount))
    db.session.add(Payment(school_id=s1.id, student_id=achieng.id, term_id=t3.id, amount=15000, method="mpesa",
                           reference="SLK8D2F1QX", receipt_no="RCT-2026-00001", recorded_by=admin1.id))
    db.session.add(Payment(school_id=s1.id, student_id=wekesa.id, term_id=t3.id, amount=22500, method="bank",
                           reference="KCB-77120934", receipt_no="RCT-2026-00002", recorded_by=admin1.id))

    # Exam + results
    exam = Exam(school_id=s1.id, term_id=terms1[1].id, class_id=cls1["Grade 7"].id, name="End of Term 2", max_score=100)
    db.session.add(exam)
    db.session.flush()
    for st, marks in ((achieng, [78, 71, 74, 82, 69, 80]), (baraka, [64, 58, 66, 61, 72, 55])):
        for (name, subj), m in zip(subj1.items(), marks):
            db.session.add(ExamResult(school_id=s1.id, exam_id=exam.id, student_id=st.id, subject_id=subj.id, marks=m))

    exam4 = Exam(school_id=s1.id, term_id=terms1[1].id, class_id=cls1["Grade 4"].id, name="End of Term 2", max_score=100)
    db.session.add(exam4)
    db.session.flush()
    for (name, subj), m in zip(subj1.items(), [88, 79, 83, 76, 91, 85]):
        db.session.add(ExamResult(school_id=s1.id, exam_id=exam4.id, student_id=wekesa.id, subject_id=subj.id, marks=m))

    # Timetable (Monday & Tuesday for Grade 7)
    day = [(time(8, 0), time(9, 0), "Mathematics", None), (time(9, 0), time(10, 0), "English", None),
           (time(10, 0), time(10, 30), None, "Break"), (time(10, 30), time(11, 30), "Integrated Science", None)]
    for dow in (1, 2):
        for a_, b_, subj, title in day:
            db.session.add(TimetableEntry(school_id=s1.id, class_id=cls1["Grade 7"].id, day_of_week=dow,
                                          start_time=a_, end_time=b_, title=title,
                                          subject_id=subj1[subj].id if subj else None))
    db.session.add(Announcement(school_id=s1.id, author_id=admin1.id, title="Term 3 opening and fee deadline",
                                content="Fees for Term 3 are payable by 30 September 2026. Pay via M-Pesa Paybill "
                                        "and quote the admission number.", priority="important"))

    db.session.add(Announcement(school_id=s1.id, author_id=admin1.id, title="Parents' meeting", audience="parents",
                                content="Class teachers will meet parents on Saturday 10 October, 9am to 12 noon."))
    db.session.add(Announcement(school_id=s1.id, author_id=admin1.id, title="Grade 4 museum trip", audience="all",
                                class_id=cls1["Grade 4"].id, priority="important",
                                content="Grade 4 visits the National Museum on Thursday. Pack a lunch."))
    db.session.add(Announcement(school_id=s1.id, author_id=admin1.id, title="Staff briefing", audience="teachers",
                                content="Marks for Term 2 must be entered by Friday."))

    # Second school, proves isolation
    s2, _, cls2, _ = _school("Tumaini Junior School", "tumaini", "Kisumu", "TJS", "junior_secondary")
    _user(s2, "admin@tumaini.demo", "Otieno", "Odhiambo", "school_admin")
    _enrol(s2, "neema@tumaini.demo", "Neema", "Atieno", cls2["Grade 7"], None, "Rose Atieno", "0722334455")
    db.session.commit()
    return {"school1": s1.id, "school2": s2.id}
