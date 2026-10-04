import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, Empty, ErrorState, Field, Loading, Modal, Pager, StatusBadge } from '../../components/ui';
import { fmtDate } from '../../utils/format';

export function Applications() {
  const [status, setStatus] = useState('');
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const qs = `?page=${page}${status ? `&status=${status}` : ''}${q ? `&q=${encodeURIComponent(q)}` : ''}`;
  const { data, meta, loading, error, reload } = useFetch(`/admissions${qs}`);
  const tabs = [['', 'All'], ['submitted', 'New'], ['under_review', 'In review'], ['changes_required', 'Changes'], ['enrolled', 'Enrolled'], ['rejected', 'Rejected']];
  return (
    <div className="stack">
      <h1>Applications</h1>
      <input className="input" placeholder="Search by name or reference" aria-label="Search applications" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
      <div className="tabs">{tabs.map(([k, l]) => <button key={k} className={`tab ${status === k ? 'active' : ''}`} onClick={() => { setStatus(k); setPage(1); }}>{l}</button>)}</div>
      {loading ? <Loading /> : error ? <ErrorState error={error} onRetry={reload} /> : data.length === 0 ? <div className="card"><Empty title="No applications found">Submitted applications will appear here.</Empty></div> : (
        <><div className="list">{data.map((a) => (
          <Link key={a.id} to={`/admin/applications/${a.id}`} className="list-row"><div className="grow"><b>{a.applicant_name}</b><div className="small muted">{a.reference_no} · {a.applying_class || 'No class'} · {fmtDate(a.submitted_at)}</div></div><StatusBadge status={a.status} /></Link>))}</div>
          <Pager meta={meta} onPage={setPage} /></>
      )}
    </div>
  );
}

export function ApplicationDetail() {
  const { id } = useParams();
  const app = useFetch(`/admissions/${id}`);
  const classes = useFetch('/classes');
  const [modal, setModal] = useState(null); // 'approve' | 'changes' | 'rejected'
  const [f, setF] = useState({ class_id: '', stream_id: '', admission_number: '', note: '' });
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  if (app.loading || classes.loading) return <Loading />;
  if (app.error) return <ErrorState error={app.error} onRetry={app.reload} />;
  const a = app.data;
  const open = ['submitted', 'under_review', 'changes_required'].includes(a.status);
  const streams = (classes.data || []).find((c) => String(c.id) === String(f.class_id))?.streams || [];

  const run = async (fn) => {
    setBusy(true); setMsg('');
    try { await fn(); setModal(null); app.reload(); } catch (e) { setMsg(e.message); } finally { setBusy(false); }
  };
  const review = (action) => run(() => api.post(`/admissions/${id}/review`, { action, note: f.note }));
  const approve = () => run(() => api.post(`/admissions/${id}/approve`, { class_id: Number(f.class_id), stream_id: f.stream_id ? Number(f.stream_id) : null, admission_number: f.admission_number || undefined, note: f.note }));
  const row = (l, v) => <div className="timeline-row"><div className="time" style={{ width: 140 }}>{l}</div><div>{v || '-'}</div></div>;

  return (
    <div className="stack">
      <div className="row between wrap"><div><Link to="/admin/applications" className="small">← Applications</Link><h1>{a.applicant_name}</h1><span className="muted small">{a.reference_no}</span></div><StatusBadge status={a.status} /></div>
      <div className="card"><h3>Learner</h3>{row('Date of birth', fmtDate(a.date_of_birth))}{row('Gender', a.gender)}{row('Nationality', a.nationality)}{row('County', a.county)}{row('Previous school', a.previous_school)}{row('Applying for', a.applying_class)}{row('Email', a.email)}{row('Phone', a.phone)}</div>
      <div className="card"><h3>Parent / guardian</h3>{row('Name', a.guardian_name)}{row('Relationship', a.guardian_relationship)}{row('Phone', a.guardian_phone)}{row('Email', a.guardian_email)}{row('Emergency contact', `${a.emergency_contact_name || '-'} ${a.emergency_contact_phone || ''}`)}</div>
      <div className="card"><h3>Documents</h3>{a.documents.length ? a.documents.map((d) => <div key={d.id}>{d.doc_type}: {d.file_name}</div>) : <p className="muted small">No documents uploaded (online upload is not available yet).</p>}</div>
      {a.review_note && <Alert type="info"><b>Note:</b> {a.review_note}</Alert>}
      {a.student_id && <Link className="btn secondary" to={`/admin/students/${a.student_id}`}>Open student record</Link>}
      {open && (
        <div className="row wrap">
          {a.status === 'submitted' && <Button variant="secondary" onClick={() => review('under_review')} loading={busy}>Start review</Button>}
          <Button variant="secondary" onClick={() => { setMsg(''); setModal('changes'); }}>Request changes</Button>
          <Button variant="danger" onClick={() => { setMsg(''); setModal('rejected'); }}>Reject</Button>
          <Button onClick={() => { setMsg(''); setF({ ...f, class_id: a.applying_class_id || '' }); setModal('approve'); }}>Approve & enrol</Button>
        </div>
      )}
      {msg && !modal && <Alert type="error">{msg}</Alert>}
      {modal === 'approve' && (
        <Modal title="Approve and enrol" onClose={() => setModal(null)}>
          <p className="muted small">This creates the student record and lets {a.first_name} log in to their student dashboard.</p>
          <Alert type="error">{msg}</Alert>
          <Field as="select" label="Class" name="class_id" required value={f.class_id} onChange={(e) => setF({ ...f, class_id: e.target.value, stream_id: '' })} options={classes.data.map((c) => ({ value: c.id, label: c.name }))} />
          <Field as="select" label="Stream (optional)" name="stream_id" value={f.stream_id} onChange={(e) => setF({ ...f, stream_id: e.target.value })} options={streams.map((s) => ({ value: s.id, label: s.name }))} />
          <Field label="Admission number (leave blank to auto-generate)" name="admission_number" value={f.admission_number} onChange={(e) => setF({ ...f, admission_number: e.target.value })} />
          <Button block onClick={approve} loading={busy} disabled={!f.class_id}>Confirm approval</Button>
        </Modal>
      )}
      {(modal === 'changes' || modal === 'rejected') && (
        <Modal title={modal === 'changes' ? 'Request changes' : 'Reject application'} onClose={() => setModal(null)}>
          <Alert type="error">{msg}</Alert>
          <Field as="textarea" label={modal === 'changes' ? 'What should the applicant fix?' : 'Reason for rejection'} name="note" required value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} />
          <Button block variant={modal === 'rejected' ? 'danger' : ''} onClick={() => review(modal)} loading={busy} disabled={!f.note.trim()}>{modal === 'changes' ? 'Send request' : 'Confirm rejection'}</Button>
        </Modal>
      )}
    </div>
  );
}
