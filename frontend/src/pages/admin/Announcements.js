import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, Empty, ErrorState, Field, Loading } from '../../components/ui';
import { fmtDate } from '../../utils/format';

export default function AnnouncementsAdmin() {
  const list = useFetch('/announcements');
  const classes = useFetch('/classes');
  const [f, setF] = useState({ title: '', content: '', audience: 'all', priority: 'normal', class_id: '' });
  const [errs, setErrs] = useState({});
  const [msg, setMsg] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setMsg({}); setErrs({});
    try { await api.post('/announcements', { ...f, class_id: f.class_id ? Number(f.class_id) : null }); setF({ ...f, title: '', content: '' }); setMsg({ type: 'success', text: 'Announcement published.' }); list.reload(); }
    catch (err) { setErrs(err.errors || {}); setMsg({ type: 'error', text: err.message }); } finally { setBusy(false); }
  };
  return (
    <div className="stack">
      <h1>Announcements</h1>
      <form className="card" onSubmit={submit} noValidate>
        <Alert type={msg.type}>{msg.text}</Alert>
        <Field label="Title" name="title" required value={f.title} onChange={set('title')} error={errs.title} />
        <Field as="textarea" label="Message" name="content" required value={f.content} onChange={set('content')} error={errs.content} />
        <div className="grid2">
          <Field as="select" label="Audience" name="audience" value={f.audience} onChange={set('audience')} options={[{ value: 'all', label: 'Everyone' }, { value: 'students', label: 'Students' }, { value: 'parents', label: 'Parents' }, { value: 'teachers', label: 'Teachers' }]} />
          <Field as="select" label="Priority" name="priority" value={f.priority} onChange={set('priority')} options={[{ value: 'normal', label: 'Normal' }, { value: 'important', label: 'Important' }, { value: 'urgent', label: 'Urgent' }]} />
        </div>
        <Field as="select" label="Limit to a class (optional)" name="class_id" value={f.class_id} onChange={set('class_id')} options={(classes.data || []).map((c) => ({ value: c.id, label: c.name }))} />
        <Button type="submit" loading={busy}>Publish</Button>
      </form>
      {list.loading ? <Loading /> : list.error ? <ErrorState error={list.error} onRetry={list.reload} /> : list.data.length === 0 ? <div className="card"><Empty title="No announcements yet" /></div> : (
        <div className="stack">{list.data.map((a) => <div key={a.id} className={`card prio-${a.priority}`}><strong>{a.title}</strong><p className="small muted">{fmtDate(a.created_at)} · {a.author} · to {a.audience}</p><p>{a.content}</p></div>)}</div>)}
    </div>
  );
}
