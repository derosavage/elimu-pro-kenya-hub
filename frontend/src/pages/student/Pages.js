import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import Icon from '../../components/Icon';
import { Alert, Button, Empty, ErrorState, Field, Loading } from '../../components/ui';
import { DAYS, fmtDate, money } from '../../utils/format';

function Page({ title, req, children, actions }) {
  if (req.loading) return <Loading />;
  if (req.error) return <ErrorState error={req.error} onRetry={req.reload} />;
  return <div className="stack"><div className="row between"><h1>{title}</h1>{actions}</div>{children(req.data)}</div>;
}

export function Results() {
  const req = useFetch('/students/me/results');
  const [sel, setSel] = useState(0);
  return (
    <Page title="My results" req={req} actions={<button className="btn secondary small no-print" onClick={() => window.print()}><Icon name="print" size={16} /> Print</button>}>
      {(exams) => {
        if (!exams.length) return <div className="card"><Empty title="No results yet">Your exam results will appear here once your teachers publish them.</Empty></div>;
        const e = exams[Math.min(sel, exams.length - 1)];
        return (<>
          <div className="tabs no-print">{exams.map((x, i) => <button key={x.exam_id} className={`tab ${i === sel ? 'active' : ''}`} onClick={() => setSel(i)}>{x.exam}</button>)}</div>
          <div className="card">
            <div className="row between"><div><strong>{e.exam}</strong><div className="muted small">{e.term}, {e.year}</div></div>
              <div className="right"><div className="stat"><div className="value">{e.mean_grade}</div></div><span className="small muted">Mean {e.mean}%</span></div></div>
            <div className="table-wrap"><table>
              <thead><tr><th>Subject</th><th>Marks</th><th>Grade</th><th>Remark</th></tr></thead>
              <tbody>{e.subjects.map((s) => <tr key={s.subject}><td>{s.subject}</td><td>{s.marks}/{s.max}</td><td><b>{s.grade}</b></td><td>{s.remark}</td></tr>)}</tbody>
              <tfoot><tr><td><b>Total</b></td><td colSpan="3"><b>{e.total}</b></td></tr></tfoot>
            </table></div>
          </div>
        </>);
      }}
    </Page>
  );
}

export function Timetable() {
  const req = useFetch('/students/me/timetable');
  const [day, setDay] = useState(Math.min(Math.max(new Date().getDay(), 1), 5));
  return (
    <Page title="Timetable" req={req}>
      {(tt) => (<>
        <div className="tabs">{Object.entries(DAYS).map(([k, v]) => <button key={k} className={`tab ${Number(k) === day ? 'active' : ''}`} onClick={() => setDay(Number(k))}>{v}</button>)}</div>
        <div className="card">{(tt[day] || []).length === 0 ? <Empty title="No lessons">Nothing is scheduled for {DAYS[day]}.</Empty> :
          tt[day].map((e) => <div key={e.id} className="timeline-row"><div className="time">{e.start_time} - {e.end_time}</div><div><b>{e.title}</b>{e.teacher && <div className="small muted">{e.teacher}</div>}</div></div>)}
        </div>
      </>)}
    </Page>
  );
}

export function Fees() {
  const req = useFetch('/students/me/fees');
  return (
    <Page title="Fees" req={req}>
      {(f) => (<>
        <div className="cards">
          <div className="card stat"><div className="label">Total fees</div><div className="value">{money(f.total_due)}</div></div>
          <div className="card stat"><div className="label">Paid</div><div className="value" style={{ color: 'var(--green)' }}>{money(f.total_paid)}</div></div>
          <div className="card stat"><div className="label">Balance</div><div className="value" style={{ color: f.balance > 0 ? 'var(--red)' : 'var(--green)' }}>{money(f.balance)}</div></div>
        </div>
        <h2>Fee structure</h2>
        <div className="card"><div className="table-wrap"><table><thead><tr><th>Term</th><th>Item</th><th className="right">Amount</th></tr></thead>
          <tbody>{f.items.length ? f.items.map((i, k) => <tr key={k}><td>{i.term} {i.year}</td><td>{i.description}</td><td className="right">{money(i.amount)}</td></tr>) : <tr><td colSpan="3" className="muted">No fees assigned yet.</td></tr>}</tbody></table></div></div>
        <h2>Payment history</h2>
        {f.payments.length === 0 ? <div className="card"><Empty title="No payments recorded" /></div> : (
          <div className="list">{f.payments.map((p) => (
            <div key={p.id} className="list-row"><div className="grow"><b>{money(p.amount)}</b><div className="small muted">{p.method.toUpperCase()} · {p.reference} · {p.term} {p.year}</div></div>
              <div className="right small"><div>{fmtDate(p.paid_at)}</div><div className="muted">{p.receipt_no}</div></div></div>))}</div>
        )}
        <p className="small muted">To pay school fees, use the payment method your school communicates (for example M-Pesa Paybill) and quote your admission number. Balances update once the school records the payment.</p>
      </>)}
    </Page>
  );
}

export function Announcements() {
  const req = useFetch('/students/me/announcements');
  return (
    <Page title="Announcements" req={req}>
      {(list) => list.length === 0 ? <div className="card"><Empty title="No announcements yet" /></div> :
        <div className="stack">{list.map((a) => <div key={a.id} className={`card prio-${a.priority}`}><div className="row between"><strong>{a.title}</strong>{a.priority !== 'normal' && <span className={`badge ${a.priority === 'urgent' ? 'red' : 'gold'}`}>{a.priority}</span>}</div>
          <p className="small muted">{fmtDate(a.created_at)} · {a.author}</p><p>{a.content}</p></div>)}</div>}
    </Page>
  );
}

export function Profile() {
  const req = useFetch('/students/me');
  const [phone, setPhone] = useState(null);
  const [msg, setMsg] = useState({});
  const [busy, setBusy] = useState(false);
  const save = async () => {
    setBusy(true); setMsg({});
    try { await api.patch('/students/me', { phone }); setMsg({ type: 'success', text: 'Phone number updated.' }); req.reload(); }
    catch (e) { setMsg({ type: 'error', text: e.errors?.phone || e.message }); } finally { setBusy(false); }
  };
  return (
    <Page title="My profile" req={req}>
      {(s) => {
        const row = (l, v) => <div className="timeline-row"><div className="time" style={{ width: 130 }}>{l}</div><div>{v || '-'}</div></div>;
        return (<>
          <div className="card">
            {row('Name', s.full_name)}{row('Admission No.', s.admission_number)}{row('Class', s.class ? `${s.class}${s.stream ? ` ${s.stream}` : ''}` : null)}
            {row('Date of birth', fmtDate(s.date_of_birth))}{row('Gender', s.gender)}{row('County', s.county)}{row('School', s.school.name)}{row('Email', s.email)}
          </div>
          <div className="card"><h3>Contact phone</h3><p className="small muted">You can update your own phone number. Other details are managed by the school office.</p>
            <Alert type={msg.type}>{msg.text}</Alert>
            <Field label="Phone" name="phone" type="tel" value={phone ?? s.phone ?? ''} onChange={(e) => setPhone(e.target.value)} />
            <Button onClick={save} loading={busy} disabled={phone === null}>Save phone</Button></div>
          <div className="card"><h3>Parent / guardian</h3>{s.guardians.map((g) => <div key={g.id} className="timeline-row"><div className="grow"><b>{g.full_name}</b><div className="small muted">{g.relationship || (g.is_emergency_contact ? 'Emergency contact' : '')}</div></div><div>{g.phone}</div></div>)}</div>
        </>);
      }}
    </Page>
  );
}

export function Settings() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [f, setF] = useState({ current_password: '', new_password: '' });
  const [msg, setMsg] = useState({});
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setMsg({});
    try { await api.post('/auth/change-password', f); setMsg({ type: 'success', text: 'Password changed.' }); setF({ current_password: '', new_password: '' }); }
    catch (err) { setMsg({ type: 'error', text: err.errors?.new_password || err.errors?.current_password || err.message }); } finally { setBusy(false); }
  };
  return (
    <div className="stack"><h1>Settings</h1>
      <form className="card" onSubmit={submit}><h3>Change password</h3><Alert type={msg.type}>{msg.text}</Alert>
        <Field label="Current password" name="cp" type="password" required autoComplete="current-password" value={f.current_password} onChange={(e) => setF({ ...f, current_password: e.target.value })} />
        <Field label="New password" name="np" type="password" required autoComplete="new-password" value={f.new_password} onChange={(e) => setF({ ...f, new_password: e.target.value })} />
        <Button type="submit" loading={busy}>Update password</Button></form>
      <Button variant="secondary" onClick={() => { logout(); navigate('/login'); }}>Sign out</Button>
    </div>
  );
}
