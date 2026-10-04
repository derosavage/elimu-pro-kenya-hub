# Database

Generated from `backend/app/models/` into `database/schema.sql` (20 tables, InnoDB, utf8mb4). No attendance tables exist.

| Group | Tables |
|---|---|
| Platform | `schools`, `users` (role column; `school_id` NULL only for super admin), `audit_logs` |
| Academic structure | `academic_years`, `terms`, `classes`, `streams`, `subjects`, `grade_bands` (school-configurable grading) |
| Learners | `students`, `guardians`, `student_applications`, `application_documents` |
| Assessment | `exams`, `exam_results`, `timetable_entries` |
| Finance & comms | `fee_structures`, `student_fees`, `payments`, `announcements` |

Rules: every school-owned table has `school_id` (indexed). Uniqueness is per school: `(school_id, admission_number)`, `(school_id, name)` for classes and
subjects, `(school_id, reference)` and `(school_id, receipt_no)` for payments. One application per applicant user (`applicant_user_id` unique);
`student_applications.student_id` and `students.user_id` link an application, its account and the enrolled student record.
Not yet modelled: teachers/staff, parents (guardians have an unused `user_id`), report cards, library, inventory, boarding, transport, notifications, messages,
student-subject and teacher-subject links.
