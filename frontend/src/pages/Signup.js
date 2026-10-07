import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth, homeFor } from '../context/AuthContext';
import { useFetch } from '../hooks/useFetch';
import { Alert, Button, ErrorState, Field, Loading } from '../components/ui';

const PHONE = /^(\+?254|0)[17]\d{8}$/;

export default function Signup() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const { data: schools, loading, error, reload } = useFetch('/schools/public');
  const [step, setStep] = useState(1);
  const [f, setF] = useState({ first_name: '', middle_name: '', last_name: '', email: '', phone: '', school_id: '', password: '', confirm: '' });
  const [errs, setErrs] = useState({});
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const validate1 = () => {
    const e = {};
    if (!f.first_name.trim()) e.first_name = 'First name is required';
    if (!f.last_name.trim()) e.last_name = 'Last name is required';
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.email)) e.email = 'Enter a valid email address';
    if (!PHONE.test(f.phone.replace(/[\s-]/g, ''))) e.phone = 'Enter a valid Kenyan number, e.g. 0712 345 678';
    return e;
  };
  const validate2 = () => {
    const e = {};
    if (!f.school_id) e.school_id = 'Select your school';
    if (f.password.length < 8 || !/[A-Za-z]/.test(f.password) || !/\d/.test(f.password)) e.password = 'At least 8 characters with letters and numbers';
    if (f.confirm !== f.password) e.confirm = 'Passwords do not match';
    return e;
  };

  const next = () => { const e = validate1(); setErrs(e); if (!Object.keys(e).length) setStep(2); };
  const submit = async (ev) => {
    ev.preventDefault();
    const e = validate2(); setErrs(e);
    if (Object.keys(e).length) return;
    setBusy(true); setMsg('');
    try {
      const user = await register({ first_name: f.first_name, middle_name: f.middle_name, last_name: f.last_name, email: f.email,
        phone: f.phone, password: f.password, school_id: Number(f.school_id) });
      navigate(homeFor(user), { replace: true });
    } catch (err) {
      setMsg(err.message); setErrs(err.errors || {});
      if (err.errors && ['first_name', 'last_name', 'email', 'phone'].some((k) => err.errors[k])) setStep(1);
    } finally { setBusy(false); }
  };

  return (
    <>
    <h1>Create your student account</h1>
    <p className="muted">Step {step} of 2. After this you will complete your admission application.</p>
    <div className="steps" aria-hidden="true"><div className="on" /><div className={step === 2 ? 'on' : ''} /></div>
    <Alert type="error">{msg}</Alert>
    {loading && <Loading />}
    {error && <ErrorState error={error} onRetry={reload} />}
    {!loading && !error && (
      <form onSubmit={submit} noValidate>
        {step === 1 ? (
          <>
            <div className="grid2">
              <Field label="First name" name="first_name" required value={f.first_name} onChange={set('first_name')} error={errs.first_name} autoComplete="given-name" />
              <Field label="Middle name" name="middle_name" value={f.middle_name} onChange={set('middle_name')} />
            </div>
            <Field label="Last name" name="last_name" required value={f.last_name} onChange={set('last_name')} error={errs.last_name} autoComplete="family-name" />
            <Field label="Email" name="email" type="email" required value={f.email} onChange={set('email')} error={errs.email} autoComplete="email" />
            <Field label="Phone number" name="phone" type="tel" required value={f.phone} onChange={set('phone')} error={errs.phone} placeholder="0712 345 678" autoComplete="tel" />
            <Button block type="button" onClick={next}>Continue</Button>
          </>
        ) : (
          <>
            <Field as="select" label="Your school" name="school_id" required value={f.school_id} onChange={set('school_id')} error={errs.school_id}
              options={(schools || []).map((s) => ({ value: s.id, label: `${s.name}${s.county ? ` (${s.county})` : ''}` }))} />
            {schools && schools.length === 0 && <Alert>No schools are accepting applications yet.</Alert>}
            <Field label="Password" name="password" type="password" required value={f.password} onChange={set('password')} error={errs.password} autoComplete="new-password" />
            <Field label="Confirm password" name="confirm" type="password" required value={f.confirm} onChange={set('confirm')} error={errs.confirm} autoComplete="new-password" />
            <div className="row"><Button type="button" variant="secondary" onClick={() => setStep(1)}>Back</Button><div className="grow"><Button block type="submit" loading={busy}>Create account</Button></div></div>
          </>
        )}
      </form>
    )}
    <p className="small muted" style={{ marginTop: '1rem' }}>Already have an account? <Link to="/login">Log in</Link></p>
    </>
  );
}