import { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, ErrorState, Field, Loading, StatusBadge } from '../../components/ui';
import { fmtDate } from '../../utils/format';

const FIELDS = ['first_name', 'middle_name', 'last_name', 'date_of_birth', 'gender', 'nationality', 'county', 'previous_school',
  'applying_class_id', 'guardian_name', 'guardian_relationship', 'guardian_phone', 'guardian_email', 'emergency_contact_name', 'emergency_contact_phone'];
const REQUIRED = { first_name: 'First name', last_name: 'Last name', date_of_birth: 'Date of birth', gender: 'Gender', nationality: 'Nationality',
  applying_class_id: 'Class applying for', guardian_name: 'Guardian name', guardian_relationship: 'Relationship', guardian_phone: 'Guardian phone',
  emergency_contact_name: 'Emergency contact name', emergency_contact_phone: 'Emergency contact phone' };
const STEP_FIELDS = [['first_name', 'last_name', 'date_of_birth', 'gender', 'nationality', 'applying_class_id'],
  ['guardian_name', 'guardian_relationship', 'guardian_phone', 'emergency_contact_name', 'emergency_contact_phone']];

export default function Application() {
  const { refresh } = useAuth();
  const app = useFetch('/admissions/my');
  const classes = useFetch('/classes');
  const [f, setF] = useState({});
  const [step, setStep] = useState(0);
  const [errs, setErrs] = useState({});
  const [msg, setMsg] = useState({ type: '', text: '' });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (app.data) setF(Object.fromEntries(FIELDS.map((k) => [k, app.data[k] ?? (k === 'nationality' ? 'Kenyan' : '')])));
  }, [app.data]);

  if (app.loading || classes.loading) return <Loading />;
  if (app.error) return <ErrorState error={app.error} onRetry={app.reload} />;
  if (classes.error) return <ErrorState error={classes.error} onRetry={classes.reload} />;
  const a = app.data;
  const editable = a.status === 'draft' || a.status === 'changes_required';
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const payload = () => ({ ...f, applying_class_id: f.applying_class_id ? Number(f.applying_class_id) : null });

  if (!editable) {
    return (
      <div className="stack">
        <h1>My application</h1>
        <div className="card accent">
          <div className="row between"><span className="muted small">Reference number</span><StatusBadge status={a.status} /></div>
          <div className="stat"><div className="value">{a.reference_no}</div></div>
          <p className="muted small">Submitted {fmtDate(a.submitted_at)}</p>
          {a.status === 'submitted' && <p>Your application has been received. The school will review it and you will see the outcome here.</p>}
          {a.status === 'under_review' && <p>The school is reviewing your application.</p>}
          {a.status === 'rejected' && <Alert type="error">{a.review_note || 'Your application was not successful.'}</Alert>}
          {a.status === 'enrolled' && <Alert type="success">You are enrolled. Use the Home tab to see your dashboard.</Alert>}
        </div>
        <div className="card"><h3>Application details</h3>
          <p>{a.applicant_name} · {a.applying_class}</p>
          <p className="muted small">Guardian: {a.guardian_name} ({a.guardian_relationship}) · {a.guardian_phone}</p></div>
      </div>
    );
  }

  const missing = (keys) => Object.fromEntries(keys.filter((k) => !f[k]).map((k) => [k, `${REQUIRED[k]} is required`]));
  const save = async (advance) => {
    setBusy(true); setMsg({ type: '', text: '' });
    try { await api.put('/admissions/my', payload()); setErrs({}); if (advance) setStep(step + 1); else setMsg({ type: 'success', text: 'Draft saved.' }); }
    catch (err) { setErrs(err.errors || {}); setMsg({ type: 'error', text: err.message }); } finally { setBusy(false); }
  };
  const nextStep = () => { const e = missing(STEP_FIELDS[step]); setErrs(e); if (!Object.keys(e).length) save(true); };
  const submit = async () => {
    const e = missing(Object.keys(REQUIRED)); setErrs(e);
    if (Object.keys(e).length) { setStep(STEP_FIELDS[0].some((k) => e[k]) ? 0 : 1); return; }
    setBusy(true);
    try { await api.post('/admissions/my/submit', payload()); await refresh(); app.reload(); }
    catch (err) { setErrs(err.errors || {}); setMsg({ type: 'error', text: err.message }); } finally { setBusy(false); }
  };
  const E = (k) => errs[k];

  return (
    <div className="stack">
      <h1>Admission application</h1>
      {a.status === 'changes_required' && <Alert type="error"><strong>The school asked for changes:</strong> {a.review_note}</Alert>}
      <div className="steps" aria-hidden="true">{[0, 1, 2].map((i) => <div key={i} className={i <= step ? 'on' : ''} />)}</div>
      <div className="card">
        <p className="muted small">Step {step + 1} of 3 · <b>{['Learner details', 'Parent / guardian', 'Review & submit'][step]}</b></p>
        <Alert type={msg.type || 'info'}>{msg.text}</Alert>
        {step === 0 && (<>
          <div className="grid2">
            <Field label="First name" name="first_name" required value={f.first_name || ''} onChange={set('first_name')} error={E('first_name')} />
            <Field label="Middle name" name="middle_name" value={f.middle_name || ''} onChange={set('middle_name')} />
            <Field label="Last name" name="last_name" required value={f.last_name || ''} onChange={set('last_name')} error={E('last_name')} />
            <Field label="Date of birth" name="date_of_birth" type="date" required value={f.date_of_birth || ''} onChange={set('date_of_birth')} error={E('date_of_birth')} />
            <Field as="select" label="Gender" name="gender" required value={f.gender || ''} onChange={set('gender')} error={E('gender')} options={[{ value: 'female', label: 'Female' }, { value: 'male', label: 'Male' }]} />
            <Field label="Nationality" name="nationality" required value={f.nationality || ''} onChange={set('nationality')} error={E('nationality')} />
            <Field label="County" name="county" value={f.county || ''} onChange={set('county')} />
            <Field label="Previous school" name="previous_school" value={f.previous_school || ''} onChange={set('previous_school')} />
          </div>
          <Field as="select" label="Class applying for" name="applying_class_id" required value={f.applying_class_id || ''} onChange={set('applying_class_id')} error={E('applying_class_id')}
            options={classes.data.map((c) => ({ value: c.id, label: c.name }))} />
        </>)}
        {step === 1 && (<>
          <div className="grid2">
            <Field label="Parent / guardian name" name="guardian_name" required value={f.guardian_name || ''} onChange={set('guardian_name')} error={E('guardian_name')} />
            <Field as="select" label="Relationship" name="guardian_relationship" required value={f.guardian_relationship || ''} onChange={set('guardian_relationship')} error={E('guardian_relationship')}
              options={['Mother', 'Father', 'Guardian', 'Other'].map((v) => ({ value: v, label: v }))} />
            <Field label="Guardian phone" name="guardian_phone" type="tel" required value={f.guardian_phone || ''} onChange={set('guardian_phone')} error={E('guardian_phone')} placeholder="0712 345 678" />
            <Field label="Guardian email" name="guardian_email" type="email" value={f.guardian_email || ''} onChange={set('guardian_email')} error={E('guardian_email')} />
            <Field label="Emergency contact name" name="emergency_contact_name" required value={f.emergency_contact_name || ''} onChange={set('emergency_contact_name')} error={E('emergency_contact_name')} />
            <Field label="Emergency contact phone" name="emergency_contact_phone" type="tel" required value={f.emergency_contact_phone || ''} onChange={set('emergency_contact_phone')} error={E('emergency_contact_phone')} />
          </div>
        </>)}
        {step === 2 && (<>
          <p><b>{[f.first_name, f.middle_name, f.last_name].filter(Boolean).join(' ')}</b><br /><span className="muted">{f.gender} · born {f.date_of_birth} · {f.nationality}{f.county ? ` · ${f.county}` : ''}</span></p>
          <p>Applying for <b>{(classes.data.find((c) => String(c.id) === String(f.applying_class_id)) || {}).name}</b></p>
          <p className="muted">Guardian: {f.guardian_name} ({f.guardian_relationship}), {f.guardian_phone}<br />Emergency: {f.emergency_contact_name}, {f.emergency_contact_phone}</p>
          <p className="small muted">Supporting documents (birth certificate, report forms) can be handed to the school office; online upload is not available yet.</p>
        </>)}
        <div className="row between wrap" style={{ marginTop: '.5rem' }}>
          <Button variant="secondary" type="button" onClick={() => (step ? setStep(step - 1) : save(false))} disabled={busy}>{step ? 'Back' : 'Save draft'}</Button>
          {step < 2 ? <Button type="button" onClick={nextStep} loading={busy}>Save & continue</Button> : <Button type="button" variant="gold" onClick={submit} loading={busy}>Submit application</Button>}
        </div>
      </div>
    </div>
  );
}
