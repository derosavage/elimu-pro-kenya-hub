import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, Empty, ErrorState, Field, Loading, Modal } from '../../components/ui';

export default function Teachers() {
  const { data, loading, error, reload } = useFetch('/teachers');
  const classes = useFetch('/classes');
  const subjects = useFetch('/subjects');
  const [add, setAdd] = useState(false);
  const [f, setF] = useState({ first_name: '', last_name: '', email: '', phone: '', password: '' });
  const [errs, setErrs] = useState({});
  const [msg, setMsg] = useState({});
  const [busy, setBusy] = useState(false);
  const [manage, setManage] = useState(null); // teacher id
  const [a, setA] = useState({ class_id: '', subject_id: '' });
  const [confirm, setConfirm] = useState(null);
  const [newSubject, setNewSubject] = useState('');
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const teacher = (data || []).find((t) => t.id === manage);

  const run = async (fn, okText) => {
    setBusy(true); setMsg({});
    try { await fn(); if (okText) setMsg({ type: 'success', text: okText }); await reload(); return true; }
    catch (e) { setErrs(e.errors || {}); setMsg({ type: 'error', text: e.message }); return false; } finally { setBusy(false); }
  };

  if (loading || classes.loading || subjects.loading) return <Loading />;
  const failed = error || classes.error || subjects.error;
  if (failed) return <ErrorState error={failed} onRetry={() => { reload(); classes.reload(); subjects.reload(); }} />;

  return (
    <div className="stack">
      <div className="row between"><h1>Teachers</h1><Button onClick={() => { setErrs({}); setMsg({}); setAdd(true); }}>Add teacher</Button></div>
      {!add && !manage && <Alert type={msg.type}>{msg.text}</Alert>}
      {data.length === 0 ? <div className="card"><Empty title="No teachers yet">Add a teacher, then assign them the classes and subjects they teach.</Empty></div> : (
        <div className="list">{data.map((t) => (
          <div key={t.id} className="list-row" style={{ flexWrap: 'wrap' }}>
            <div className="grow"><b>{t.full_name}</b> {!t.is_active && <span className="badge red">Inactive</span>}
              <div className="small muted">{t.email}</div>
              <div className="small">{t.assignments.length ? t.assignments.map((x) => `${x.class} ${x.subject}`).join(' · ') : <span className="muted">Not assigned to any class</span>}</div></div>
            <Button variant="secondary" className="small" onClick={() => { setMsg({}); setA({ class_id: '', subject_id: '' }); setManage(t.id); }}>Assignments</Button>
            <Button variant="secondary" className="small" onClick={() => setConfirm(t)}>{t.is_active ? 'Deactivate' : 'Activate'}</Button>
          </div>))}</div>
      )}

      {add && (
        <Modal title="Add teacher" onClose={() => setAdd(false)}>
          <Alert type="error">{msg.type === 'error' ? msg.text : ''}</Alert>
          <div className="grid2">
            <Field label="First name" name="fn" required value={f.first_name} onChange={set('first_name')} error={errs.first_name} />
            <Field label="Last name" name="ln" required value={f.last_name} onChange={set('last_name')} error={errs.last_name} />
          </div>
          <Field label="Email" name="em" type="email" required value={f.email} onChange={set('email')} error={errs.email} />
          <Field label="Phone" name="ph" type="tel" value={f.phone} onChange={set('phone')} error={errs.phone} />
          <Field label="Temporary password" name="pw" type="password" required value={f.password} onChange={set('password')} error={errs.password} />
          <Button block loading={busy} onClick={async () => { if (await run(() => api.post('/teachers', f), 'Teacher added. Now assign their classes and subjects.')) { setAdd(false); setF({ first_name: '', last_name: '', email: '', phone: '', password: '' }); } }}>Create teacher</Button>
        </Modal>
      )}

      {teacher && (
        <Modal title={`Assignments: ${teacher.full_name}`} onClose={() => setManage(null)}>
          <Alert type={msg.type}>{msg.text}</Alert>
          {teacher.assignments.length === 0 ? <p className="muted small">Nothing assigned yet.</p> : (
            <div className="list" style={{ marginBottom: '1rem' }}>{teacher.assignments.map((x) => (
              <div key={x.id} className="list-row"><div className="grow">{x.class} · <b>{x.subject}</b></div>
                <Button variant="secondary" className="small" loading={busy} onClick={() => run(() => api.delete(`/teachers/${teacher.id}/assignments/${x.id}`), 'Assignment removed.')}>Remove</Button></div>))}</div>)}
          <div className="grid2">
            <Field as="select" label="Class" name="ac" value={a.class_id} onChange={(e) => setA({ ...a, class_id: e.target.value })} options={classes.data.map((c) => ({ value: c.id, label: c.name }))} />
            <Field as="select" label="Subject" name="as" value={a.subject_id} onChange={(e) => setA({ ...a, subject_id: e.target.value })} options={subjects.data.map((s) => ({ value: s.id, label: s.name }))} />
          </div>
          <Button block loading={busy} disabled={!a.class_id || !a.subject_id} onClick={() => run(() => api.post(`/teachers/${teacher.id}/assignments`, { class_id: Number(a.class_id), subject_id: Number(a.subject_id) }), 'Assigned.')}>Assign</Button>
          <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '1rem 0' }} />
          <p className="small muted">Subject missing from the list? Add it here.</p>
          <div className="row"><input className="input" aria-label="New subject" placeholder="e.g. Physics" value={newSubject} onChange={(e) => setNewSubject(e.target.value)} />
            <Button variant="secondary" disabled={!newSubject.trim()} onClick={async () => { if (await run(() => api.post('/subjects', { name: newSubject }), 'Subject added.')) { setNewSubject(''); subjects.reload(); } }}>Add</Button></div>
        </Modal>
      )}

      {confirm && (
        <Modal title="Are you sure?" onClose={() => setConfirm(null)}>
          <p>{confirm.is_active ? `${confirm.full_name} will no longer be able to log in.` : `${confirm.full_name} will be able to log in again.`}</p>
          <div className="row"><Button variant="secondary" onClick={() => setConfirm(null)}>Cancel</Button>
            <Button variant={confirm.is_active ? 'danger' : ''} loading={busy} onClick={async () => { if (await run(() => api.patch(`/teachers/${confirm.id}`, { is_active: !confirm.is_active }))) setConfirm(null); }}>Confirm</Button></div>
        </Modal>
      )}
    </div>
  );
}
