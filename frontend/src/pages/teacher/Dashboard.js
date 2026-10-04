import { Link } from 'react-router-dom';
import { useFetch } from '../../hooks/useFetch';
import { Empty, ErrorState, Loading } from '../../components/ui';
import { fmtDate, greeting } from '../../utils/format';

export default function TeacherDashboard() {
  const { data: d, loading, error, reload } = useFetch('/teacher/dashboard');
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="stack">
      <div>
        <h1>{greeting()}, {d.teacher.first_name}</h1>
        <p className="muted">{d.school.name}{d.term ? ` · ${d.term.name}, ${d.term.year}` : ''}</p>
      </div>
      <div className="cards">
        <div className="card stat"><div className="label">My classes</div><div className="value">{d.classes.length}</div></div>
        <div className="card stat"><div className="label">My learners</div><div className="value">{d.total_students}</div></div>
      </div>
      <div className="row"><Link className="btn" to="/teacher/results">Enter results</Link><Link className="btn secondary" to="/teacher/classes">View classes</Link></div>

      <section>
        <h2>My classes and subjects</h2>
        {d.classes.length === 0 ? <div className="card"><Empty title="No classes assigned yet">Ask your school administrator to assign you to classes and subjects.</Empty></div> : (
          <div className="list">{d.classes.map((c) => (
            <Link key={c.class_id} to={`/teacher/classes?class=${c.class_id}`} className="list-row">
              <div className="grow"><b>{c.class}</b><div className="small muted">{c.subjects.map((s) => s.name).join(', ')}</div></div>
              <span className="badge blue">{c.student_count} learners</span></Link>))}</div>
        )}
      </section>

      <section>
        <h2>Recent exams</h2>
        {d.recent_exams.length === 0 ? <div className="card muted small">No exams yet for your classes. Create one from the results page.</div> :
          <div className="list">{d.recent_exams.map((e) => <div key={e.id} className="list-row"><div className="grow"><b>{e.name}</b><div className="small muted">{e.term}</div></div></div>)}</div>}
      </section>

      <section>
        <div className="row between"><h2>Staff notices</h2><Link to="/teacher/announcements" className="small">See all</Link></div>
        {d.announcements.length === 0 ? <div className="card muted small">No announcements.</div> : d.announcements.map((a) => (
          <div key={a.id} className={`card prio-${a.priority}`} style={{ marginBottom: '.75rem' }}><strong>{a.title}</strong><p className="small muted">{fmtDate(a.created_at)} · {a.author}</p><p>{a.content}</p></div>))}
      </section>
    </div>
  );
}
