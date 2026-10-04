import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useFetch } from '../../hooks/useFetch';
import { Empty, ErrorState, Loading } from '../../components/ui';
import { initials } from '../../utils/format';

export default function TeacherClasses() {
  const classes = useFetch('/teacher/classes');
  const [params, setParams] = useSearchParams();
  const [sel, setSel] = useState(params.get('class') || '');
  useEffect(() => { if (!sel && classes.data && classes.data.length) setSel(String(classes.data[0].class_id)); }, [classes.data, sel]);
  const roster = useFetch(sel ? `/teacher/classes/${sel}/students` : null);
  const [q, setQ] = useState('');

  if (classes.loading) return <Loading />;
  if (classes.error) return <ErrorState error={classes.error} onRetry={classes.reload} />;
  if (!classes.data.length) return <div className="card"><Empty title="No classes assigned yet">Ask your school administrator to assign you to classes and subjects.</Empty></div>;
  const cur = classes.data.find((c) => String(c.class_id) === String(sel));
  const rows = (roster.data || []).filter((s) => `${s.full_name} ${s.admission_number}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="stack">
      <h1>My classes</h1>
      <div className="tabs">{classes.data.map((c) => (
        <button key={c.class_id} className={`tab ${String(c.class_id) === String(sel) ? 'active' : ''}`} onClick={() => { setSel(String(c.class_id)); setParams({ class: c.class_id }); }}>{c.class}</button>))}</div>
      {cur && <p className="muted small">You teach: {cur.subjects.map((s) => s.name).join(', ')}</p>}
      <input className="input" placeholder="Search learners" aria-label="Search learners" value={q} onChange={(e) => setQ(e.target.value)} />
      {roster.loading ? <Loading /> : roster.error ? <ErrorState error={roster.error} onRetry={roster.reload} /> : rows.length === 0 ? <div className="card"><Empty title="No learners found" /></div> : (
        <div className="list">{rows.map((s) => (
          <div key={s.id} className="list-row"><div className="avatar">{initials(s.full_name)}</div>
            <div className="grow"><b>{s.full_name}</b><div className="small muted">{s.admission_number}{s.stream ? ` · ${s.stream}` : ''}</div></div></div>))}</div>
      )}
    </div>
  );
}
