import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, Empty, ErrorState, Loading, Modal, Pager } from '../../components/ui';
import { fmtDate, initials, money } from '../../utils/format';

export function Students() {
  const [q, setQ] = useState('');
  const [cls, setCls] = useState('');
  const [page, setPage] = useState(1);
  const classes = useFetch('/classes');
  const { data, meta, loading, error, reload } = useFetch(`/students?page=${page}${cls ? `&class_id=${cls}` : ''}${q ? `&q=${encodeURIComponent(q)}` : ''}`);
  return (
    <div className="stack">
      <h1>Students</h1>
      <div className="grid2">
        <input className="input" placeholder="Search name or admission number" aria-label="Search students" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <select className="input" aria-label="Filter by class" value={cls} onChange={(e) => { setCls(e.target.value); setPage(1); }}><option value="">All classes</option>{(classes.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
      </div>
      {loading ? <Loading /> : error ? <ErrorState error={error} onRetry={reload} /> : data.length === 0 ? <div className="card"><Empty title="No students found">Students appear here once their applications are approved.</Empty></div> : (
        <><div className="list">{data.map((s) => (
          <Link key={s.id} to={`/admin/students/${s.id}`} className="list-row"><div className="avatar">{initials(s.full_name)}</div>
            <div className="grow"><b>{s.full_name}</b><div className="small muted">{s.admission_number} · {s.class}{s.stream ? ` ${s.stream}` : ''}</div></div>
            {s.status !== 'active' && <span className="badge">{s.status}</span>}</Link>))}</div><Pager meta={meta} onPage={setPage} /></>
      )}
    </div>
  );
}

export function StudentDetail() {
  const { id } = useParams();
  const st = useFetch(`/students/${id}`);
  const [confirm, setConfirm] = useState(null);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  if (st.loading) return <Loading />;
  if (st.error) return <ErrorState error={st.error} onRetry={st.reload} />;
  const s = st.data;
  const change = async () => {
    setBusy(true); setMsg('');
    try { await api.patch(`/students/${id}`, { status: confirm.status }); setConfirm(null); st.reload(); } catch (e) { setMsg(e.message); } finally { setBusy(false); }
  };
  const row = (l, v) => <div className="timeline-row"><div className="time" style={{ width: 140 }}>{l}</div><div>{v || '-'}</div></div>;
  return (
    <div className="stack">
      <Link to="/admin/students" className="small">← Students</Link>
      <div className="greet"><div className="avatar" style={{ width: 56, height: 56 }}>{initials(s.full_name)}</div><div><h1>{s.full_name}</h1><span className="muted small">Adm No. {s.admission_number} · {s.status}</span></div></div>
      <div className="card">{row('Class', `${s.class || '-'}${s.stream ? ` ${s.stream}` : ''}`)}{row('Date of birth', fmtDate(s.date_of_birth))}{row('Gender', s.gender)}{row('County', s.county)}{row('Previous school', s.previous_school)}{row('Phone', s.phone)}{row('Email', s.email)}{row('Admitted', fmtDate(s.admitted_on))}</div>
      <div className="card"><h3>Guardians</h3>{s.guardians.map((g) => <div key={g.id} className="timeline-row"><div className="grow"><b>{g.full_name}</b><div className="small muted">{g.relationship || 'Emergency contact'}</div></div><div>{g.phone}</div></div>)}</div>
      {s.fees && <div className="card"><h3>Fees</h3>{row('Total due', money(s.fees.total_due))}{row('Paid', money(s.fees.total_paid))}{row('Balance', money(s.fees.balance))}</div>}
      {s.results && <div className="card"><h3>Academic history</h3>{s.results.length === 0 ? <p className="muted small">No results recorded.</p> : s.results.map((r) => <div key={r.exam_id} className="timeline-row"><div className="grow">{r.exam} ({r.term} {r.year})</div><b>{r.mean_grade} · {r.mean}%</b></div>)}</div>}
      <div className="row wrap no-print">
        {s.status === 'active' ? <>
          <Button variant="secondary" onClick={() => setConfirm({ status: 'transferred', label: 'transfer' })}>Transfer</Button>
          <Button variant="secondary" onClick={() => setConfirm({ status: 'graduated', label: 'mark as graduated' })}>Graduate</Button>
          <Button variant="danger" onClick={() => setConfirm({ status: 'inactive', label: 'deactivate' })}>Deactivate</Button></>
          : <Button onClick={() => setConfirm({ status: 'active', label: 'reactivate' })}>Reactivate</Button>}
      </div>
      {confirm && <Modal title="Are you sure?" onClose={() => setConfirm(null)}>
        <p>You are about to <b>{confirm.label}</b> {s.full_name}. {confirm.status !== 'active' ? 'Their login will be disabled.' : ''}</p><Alert type="error">{msg}</Alert>
        <div className="row"><Button variant="secondary" onClick={() => setConfirm(null)}>Cancel</Button><Button variant={confirm.status === 'inactive' ? 'danger' : ''} loading={busy} onClick={change}>Confirm</Button></div></Modal>}
    </div>
  );
}
