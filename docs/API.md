# API reference (base path `/api`, JSON)

Success: `{"success": true, "data": ..., "message"?: ..., "meta"?: {page, per_page, total, pages}}`.
Error: `{"success": false, "message": "...", "errors"?: {field: message}}` with 400/401/403/404/409/422/503.
Send `Authorization: Bearer <token>`. The role and school always come from the database user, never from the request.
Other schools' record IDs return **404**.

## Auth
| Method & path | Who | Notes |
|---|---|---|
| POST `/auth/register` | public | Student signup: `school_id, first_name, last_name, email, phone, password` (+`middle_name`). Creates account + draft application, returns token |
| POST `/auth/login` | public | `email, password` → `{token, user}` |
| GET `/auth/me` | any | user + `is_enrolled`, `application_status` for students |
| POST `/auth/change-password` | any | `current_password, new_password` |

## Schools
GET `/schools/public` (public, active schools with admissions open) · GET/PUT `/schools/me` · GET `/schools/overview` (admin, bursar) ·
GET/POST `/schools`, PATCH `/schools/<id>/status` (super admin).

## Admissions
Student: GET/PUT `/admissions/my`, POST `/admissions/my/submit`.
Admin/principal/deputy: GET `/admissions?status=&q=&page=`, GET `/admissions/<id>`, POST `/admissions/<id>/review` (`action`: under_review | changes_required | rejected, `note` required for the last two),
POST `/admissions/<id>/approve` (`class_id`, optional `stream_id`, `admission_number`, `note`) → creates the student.

## Students
Student: GET/PATCH `/students/me` (phone only), `/students/me/dashboard`, `/me/results`, `/me/fees`, `/me/timetable`, `/me/announcements`.
Staff: GET `/students?q=&class_id=&status=&page=`, GET `/students/<id>`, PATCH `/students/<id>` (admin: `class_id, stream_id, status`).

## Academics
GET/POST `/classes`, POST `/classes/<id>/streams`, GET/POST `/subjects`, GET `/terms`, GET `/grading`, GET/POST `/exams`,
POST `/results` (`exam_id, subject_id, entries[{student_id, marks, remark}]`), POST `/timetable`.

## Finance
GET/POST `/fees/structures`, POST `/fees/assign` (`term_id`), GET `/fees/balances`, GET/POST `/payments`,
POST `/payments/mpesa/stk-push` (503 unless configured; untested).

## Announcements
GET `/announcements` (students see only their audience/class), POST `/announcements` (admin).
