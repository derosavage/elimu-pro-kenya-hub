import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, Empty, ErrorState, Field, Loading, Modal, Pager } from '../../components/ui';
import { money } from '../../utils/format';

export default function FeesAdmin() {
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const bal = useFetch(`/fees/balances?page=${page}${q ? `&q=${encodeURIComponent(q)}` : ''}`);
  const terms = useFetch('/terms');
  const [pay, setPay] = useState(null);
  const [f, setF] = useState({ amount: '', method: 'mpesa', reference: '' });
  const [msg, setMsg] = useState({});
  const [busy, setBusy] = useState(false);
  const current = (terms.data || []).find((t) => t.is_current);

  const record = async () => {
    setBusy(true); setMsg({});
    try {
      await api.post('/payments', { student_id: pay.student_id, term_id: current.id, amount: Number(f.amount), method: f.method, reference: f.reference });
      setPay(null); setF({ amount: '', method: 'mpesa', reference: '' }); setMsg({ type: 'success', text: 'Payment recorded.' }); bal.reload();
    } catch (e) { setMsg({ type: 'error', text: e.message }); } finally { setBusy(false); }
  };
  const assign = async () => {
    setMsg({});
    try { const r = await api.post('/fees/assign', { term_id: current.id }); setMsg({ type: 'success', text: `${r.data.created} fee items assigned.` }); bal.reload(); }
    catch (e) { setMsg({ type: 'error', text: e.message }); }
  };

  return (
    <div className="stack">
      <div className="row between wrap"><h1>Fees & payments</h1>{current && <Button variant="secondary" onClick={assign}>Assign {current.name} fees</Button>}</div>
      <Alert type={msg.type}>{msg.text}</Alert>
      <input className="input" placeholder="Search student or admission number" aria-label="Search" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
      {bal.loading ? <Loading /> : bal.error ? <ErrorState error={bal.error} onRetry={bal.reload} /> : bal.data.length === 0 ? <div className="card"><Empty title="No students found" /></div> : (
        <><div className="list">{bal.data.map((b) => (
          <div key={b.student_id} className="list-row"><div className="grow"><b>{b.name}</b><div className="small muted">{b.admission_number} · {b.class}</div></div>
            <div className="right"><b style={{ color: b.balance > 0 ? 'var(--red)' : 'var(--green)' }}>{money(b.balance)}</b><div className="small muted">of {money(b.due)}</div></div>
            <Button variant="secondary" className="small" disabled={!current} onClick={() => { setMsg({}); setPay(b); }}>Record</Button></div>))}</div><Pager meta={bal.meta} onPage={setPage} /></>
      )}
      {pay && (
        <Modal title={`Record payment: ${pay.name}`} onClose={() => setPay(null)}>
          <p className="small muted">Records a payment received by the school ({current?.name}, {current?.year}). Live M-Pesa STK Push is not enabled in this build.</p>
          <Alert type={msg.type === 'error' ? 'error' : undefined}>{msg.type === 'error' ? msg.text : ''}</Alert>
          <Field label="Amount (KES)" name="amount" type="number" min="1" required value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} />
          <Field as="select" label="Method" name="method" required value={f.method} onChange={(e) => setF({ ...f, method: e.target.value })} options={[{ value: 'mpesa', label: 'M-Pesa' }, { value: 'bank', label: 'Bank' }, { value: 'cash', label: 'Cash' }]} />
          <Field label="Reference (M-Pesa code / bank slip / receipt book no.)" name="reference" required value={f.reference} onChange={(e) => setF({ ...f, reference: e.target.value })} />
          <Button block onClick={record} loading={busy} disabled={!f.amount || !f.reference}>Save payment</Button>
        </Modal>
      )}
    </div>
  );
}
