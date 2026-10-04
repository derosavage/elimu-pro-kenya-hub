# Update: parent role, parent portal and richer demo data

Copy these files over your existing project (paths are relative to `ElimuPro/`). No schema change: parents use the existing `users` and `guardians.user_id` columns.

## Get the new demo data
The seed script was extended (parents, a sibling, a third applicant, more announcements, Grade 4 results and a bank payment).
On your development database run, inside `backend/`:

    python reset_demo.py        # type YES when asked; drops all tables, recreates them, reloads demo data

It refuses to run if any school that is not marked demo exists. `python seed.py` still only seeds an empty database.

## New demo logins (password Demo@1234)
- mary.otieno@mwangaza.demo : parent of Achieng (Grade 7) and Wekesa (Grade 4), one login, two children
- james.mwangi@mwangaza.demo : parent of Baraka

## Behaviour
- Admin > Students > open a student > Guardians > "Create login" gives a guardian a parent login. Entering the email of an existing parent (and no password) links a sibling to that login.
- Admin > Parents lists parent logins with their children.
- Parents see only children linked to them; any other student id returns 404. Parents get 403 on all staff, teacher and student endpoints.
- Existing tests were updated for the larger seed (3 students, 3 pending applications in the overview test).

Checked: `pytest -q` in backend/ = 43 passed (SQLite, not MySQL). `reset_demo.py` and a parent login/dashboard were exercised against a live local server on SQLite. Frontend `react-scripts build` compiles. Not tried in a browser.
