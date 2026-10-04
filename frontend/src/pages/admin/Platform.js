import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, ErrorState, Field, Loading, Modal } from '../../components/ui';

export default function Platform() {
  const { data, loading, error, reload } = useFetch('/schools');
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ name: '', slug: '', admin_email: '', admin_password: '' });
  const [errs, setErrs] = useState({});
  const [msg, setMsg] = useState('');
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const toggle = async (s) => { try { await api.patch(`/schools/${s.id}/status`, { is_active: !s.is_active }); reload(); } catch (e) { setMsg(e.message); } };
  const create = async () => {
    setErrs({}); setMsg('');
    try { await api.post('/schools', f); setOpen(false); setF({ name: '', slug: '', admin_email: '', admin_password: '' }); reload(); }
    catch (e) { setErrs(e.errors || {}); setMsg(e.message); }
  };
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="stack">
      <div className="row between"><h1>Schools</h1><Button onClick={() => setOpen(true)}>Add school</Button></div>
      <Alert type="error">{!open && msg}</Alert>
      <div className="list">{data.map((s) => (
        <div key={s.id} className="list-row"><div className="grow"><b>{s.name}</b><div className="small muted">{s.county} · {s.student_count} students {s.is_demo ? '· demo' : ''}</div></div>
          <span className={`badge ${s.is_active ? 'green' : 'red'}`}>{s.is_active ? 'Active' : 'Inactive'}</span>
          <Button variant="secondary" className="small" onClick={() => toggle(s)}>{s.is_active ? 'Deactivate' : 'Activate'}</Button></div>))}</div>
      {open && <Modal title="Add school" onClose={() => setOpen(false)}><Alert type="error">{msg}</Alert>
        <Field label="School name" name="name" required value={f.name} onChange={set('name')} error={errs.name} />
        <Field label="Short code (letters, numbers, hyphens)" name="slug" required value={f.slug} onChange={set('slug')} error={errs.slug} />
        <Field label="Administrator email" name="admin_email" type="email" required value={f.admin_email} onChange={set('admin_email')} error={errs.admin_email} />
        <Field label="Temporary password" name="admin_password" type="password" required value={f.admin_password} onChange={set('admin_password')} error={errs.admin_password} />
        <Button block onClick={create}>Create school</Button></Modal>}
    </div>
  );
}
