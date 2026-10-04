import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, Empty, ErrorState, Field, Loading } from '../../components/ui';

export default function Classes() {
  const { data, loading, error, reload } = useFetch('/classes');
  const [name, setName] = useState('');
  const [streamNames, setStreamNames] = useState({});
  const [msg, setMsg] = useState({});
  const run = async (fn, ok) => {
    setMsg({});
    try { await fn(); setMsg({ type: 'success', text: ok }); reload(); } catch (e) { setMsg({ type: 'error', text: e.errors?.name || e.message }); }
  };
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="stack">
      <h1>Classes & streams</h1>
      <Alert type={msg.type}>{msg.text}</Alert>
      <form className="card row wrap" onSubmit={(e) => { e.preventDefault(); run(async () => { await api.post('/classes', { name, level_order: data.length + 1 }); setName(''); }, 'Class added.'); }}>
        <div className="grow"><Field label="New class (e.g. Grade 5, Form 1)" name="cls" value={name} onChange={(e) => setName(e.target.value)} required /></div>
        <Button type="submit" disabled={!name.trim()}>Add class</Button>
      </form>
      {data.length === 0 ? <div className="card"><Empty title="No classes yet">Add your first class above.</Empty></div> : data.map((c) => (
        <div key={c.id} className="card">
          <div className="row between"><h3>{c.name}</h3><span className="muted small">{c.streams.length} stream{c.streams.length === 1 ? '' : 's'}</span></div>
          <div className="row wrap" style={{ marginBottom: '.75rem' }}>{c.streams.map((s) => <span key={s.id} className="badge blue">{s.name}</span>)}</div>
          <form className="row" onSubmit={(e) => { e.preventDefault(); run(async () => { await api.post(`/classes/${c.id}/streams`, { name: streamNames[c.id] }); setStreamNames({ ...streamNames, [c.id]: '' }); }, 'Stream added.'); }}>
            <input className="input" aria-label={`New stream for ${c.name}`} placeholder="New stream, e.g. East" value={streamNames[c.id] || ''} onChange={(e) => setStreamNames({ ...streamNames, [c.id]: e.target.value })} />
            <Button type="submit" variant="secondary" disabled={!(streamNames[c.id] || '').trim()}>Add</Button>
          </form>
        </div>))}
    </div>
  );
}
