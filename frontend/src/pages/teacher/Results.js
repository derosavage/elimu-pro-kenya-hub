import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, Empty, ErrorState, Field, Loading, Modal } from '../../components/ui';

/* Mark-entry screen. Flow: class → subject → exam → mark sheet.
   Grades shown here are a live preview computed with the school's own grade bands (GET /grading);
   the backend re-validates everything on save. */
export default function TeacherResults() {
  const classes = useFetch('/teacher/classes');
  const grading = useFetch('/grading');
  const terms = useFetch('/terms');
  const [classId, setClassId] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [examId, setExamId] = useState('');
  const exams = useFetch(classId ? `/exams?class_id=${classId}` : null);
  const sheet = useFetch(examId && subjectId ? `/results?exam_id=${examId}&subject_id=${subjectId}` : null);

  const [values, setValues] = useState({});   // {student_id: {marks, remark}}
  const [dirty, setDirty] = useState(false);
  const [msg, setMsg] = useState({});
  const [rowErrs, setRowErrs] = useState({});
  const [busy, setBusy] = useState(false);
  const [newExam, setNewExam] = useState(false);
  const [ef, setEf] = useState({ name: '', max_score: '100' });
  const [efErr, setEfErr] = useState('');

  const cls = (classes.data || []).find((c) => String(c.class_id) === String(classId));
  const currentTerm = (terms.data || []).find((t) => t.is_current);

  useEffect(() => {
    if (sheet.data) {
      setValues(Object.fromEntries(sheet.data.students.map((s) => [s.student_id, { marks: s.marks ?? '', remark: s.remark || '' }])));
      setDirty(false); setRowErrs({}); setMsg({});
    }
  }, [sheet.data]);

  const max = sheet.data?.exam.max_score || 100;
  const gradeOf = useMemo(() => {
    const bands = grading.data || [];
    return (m) => { const pct = (m / max) * 100; const b = bands.find((x) => pct >= x.min_mark); return b ? b.grade : ''; };
  }, [grading.data, max]);

  const resetBelow = (level) => { if (level <= 1) setSubjectId(''); if (level <= 2) setExamId(''); setMsg({}); };
  const guardLeave = (fn) => () => { if (dirty && !window.confirm('You have unsaved marks. Discard them?')) return; fn(); };

  const setCell = (id, k, v) => { setValues({ ...values, [id]: { ...values[id], [k]: v } }); setDirty(true); setMsg({}); };
  const invalid = (v) => v !== '' && (isNaN(Number(v)) || Number(v) < 0 || Number(v) > max);

  const save = async () => {
    const entries = sheet.data.students.filter((s) => values[s.student_id]?.marks !== '')
      .map((s) => ({ student_id: s.student_id, marks: Number(values[s.student_id].marks), remark: values[s.student_id].remark || null }));
    const bad = {};
    sheet.data.students.forEach((s) => { if (invalid(values[s.student_id]?.marks)) bad[s.student_id] = `Enter a mark from 0 to ${max}`; });
    setRowErrs(bad);
    if (Object.keys(bad).length) return setMsg({ type: 'error', text: 'Fix the highlighted marks before saving.' });
    if (!entries.length) return setMsg({ type: 'error', text: 'Enter at least one mark.' });
    setBusy(true); setMsg({});
    try {
      const r = await api.post('/results', { exam_id: Number(examId), subject_id: Number(subjectId), entries });
      setDirty(false); setMsg({ type: 'success', text: r.message }); sheet.reload();
    } catch (e) {
      // backend errors are keyed by entry index; map them back to students
      const mapped = {};
      Object.entries(e.errors || {}).forEach(([i, m]) => { if (entries[i]) mapped[entries[i].student_id] = m; });
      setRowErrs(mapped); setMsg({ type: 'error', text: e.message });
    } finally { setBusy(false); }
  };

  const createExam = async () => {
    setEfErr('');
    if (!ef.name.trim()) return setEfErr('Give the exam a name, e.g. Mid-Term');
    if (!currentTerm) return setEfErr('No current term is set. Ask your administrator.');
    try {
      const r = await api.post('/exams', { name: ef.name, class_id: Number(classId), term_id: currentTerm.id, max_score: Number(ef.max_score) || 100 });
      setNewExam(false); setEf({ name: '', max_score: '100' }); await exams.reload(); setExamId(String(r.data.id));
    } catch (e) { setEfErr(e.message); }
  };

  if (classes.loading || grading.loading || terms.loading) return <Loading />;
  const failed = classes.error || grading.error || terms.error;
  if (failed) return <ErrorState error={failed} onRetry={() => { classes.reload(); grading.reload(); terms.reload(); }} />;
  if (!classes.data.length) return <div className="card"><Empty title="No classes assigned yet">Ask your school administrator to assign you to a class and subject before entering results.</Empty></div>;

  const filled = Object.values(values).filter((v) => v.marks !== '' && !invalid(v.marks)).length;

  return (
    <div className="stack">
      <h1>Enter results</h1>
      <div className="card">
        <div className="grid2">
          <Field as="select" label="Class" name="class" value={classId} onChange={(e) => { guardLeave(() => { setClassId(e.target.value); resetBelow(0); })(); }}
            options={classes.data.map((c) => ({ value: c.class_id, label: c.class }))} />
          <Field as="select" label="Subject" name="subject" value={subjectId} disabled={!cls} onChange={(e) => guardLeave(() => { setSubjectId(e.target.value); setExamId(''); })()}
            options={(cls?.subjects || []).map((s) => ({ value: s.id, label: s.name }))} />
        </div>
        <div className="row wrap" style={{ alignItems: 'flex-end' }}>
          <div className="grow"><Field as="select" label="Exam" name="exam" value={examId} disabled={!subjectId} onChange={(e) => guardLeave(() => setExamId(e.target.value))()}
            options={(exams.data || []).map((x) => ({ value: x.id, label: `${x.name} (${x.term}, out of ${x.max_score})` }))} /></div>
          <div style={{ marginBottom: '1rem' }}><Button variant="secondary" disabled={!classId} onClick={() => { setEfErr(''); setNewExam(true); }}>New exam</Button></div>
        </div>
        {exams.error && <ErrorState error={exams.error} onRetry={exams.reload} />}
        {classId && exams.data && exams.data.length === 0 && <p className="small muted">No exams for this class yet. Use "New exam" to create one.</p>}
      </div>

      {sheet.loading && <Loading />}
      {sheet.error && <ErrorState error={sheet.error} onRetry={sheet.reload} />}
      {sheet.data && (
        <div className="stack">
          <div className="row between wrap">
            <div><h2>{sheet.data.subject.name}</h2><span className="muted small">{sheet.data.exam.name} · {sheet.data.exam.term} · marks out of {max}</span></div>
            <span className="small muted">{filled} of {sheet.data.students.length} entered{dirty ? ' · unsaved changes' : ''}</span>
          </div>
          <Alert type={msg.type}>{msg.text}</Alert>
          {sheet.data.students.length === 0 ? <div className="card"><Empty title="No active learners in this class" /></div> : (
            <div className="list">{sheet.data.students.map((s) => {
              const v = values[s.student_id] || { marks: '', remark: '' };
              const bad = rowErrs[s.student_id] || (invalid(v.marks) ? `Enter a mark from 0 to ${max}` : '');
              return (
                <div key={s.student_id} className="list-row" style={{ flexWrap: 'wrap', alignItems: 'flex-start' }}>
                  <div className="grow" style={{ minWidth: 150 }}><b>{s.full_name}</b><div className="small muted">{s.admission_number}{s.stream ? ` · ${s.stream}` : ''}</div></div>
                  <div style={{ width: 92 }}>
                    <input className={`input ${bad ? 'invalid' : ''}`} inputMode="decimal" aria-label={`Marks for ${s.full_name}`} placeholder={`/${max}`}
                      value={v.marks} onChange={(e) => setCell(s.student_id, 'marks', e.target.value)} />
                  </div>
                  <div style={{ width: 44, textAlign: 'center', paddingTop: 10 }}>{v.marks !== '' && !invalid(v.marks) ? <span className="badge blue">{gradeOf(Number(v.marks))}</span> : ''}</div>
                  <div style={{ flexBasis: '100%' }}>
                    <input className="input" aria-label={`Remark for ${s.full_name}`} placeholder="Teacher remark (optional)" maxLength={255} value={v.remark} onChange={(e) => setCell(s.student_id, 'remark', e.target.value)} />
                    {bad && <div className="err small" style={{ color: 'var(--red)' }} role="alert">{bad}</div>}
                  </div>
                </div>);
            })}</div>
          )}
          <div className="row between" style={{ position: 'sticky', bottom: 'calc(64px + var(--safe-b))' }}>
            <span />
            <Button onClick={save} loading={busy} disabled={!dirty}>Save marks</Button>
          </div>
        </div>
      )}
      {!sheet.data && !sheet.loading && examId === '' && subjectId && <p className="muted small">Choose an exam to open the mark sheet.</p>}
      <p className="small muted">Learners see their results as soon as you save. <Link to="/teacher/classes">View class lists</Link></p>

      {newExam && (
        <Modal title="New exam" onClose={() => setNewExam(false)}>
          <p className="small muted">For {cls?.class}{currentTerm ? `, ${currentTerm.name} ${currentTerm.year}` : ''}.</p>
          <Alert type="error">{efErr}</Alert>
          <Field label="Exam name" name="ename" required placeholder="e.g. Mid-Term, End of Term" value={ef.name} onChange={(e) => setEf({ ...ef, name: e.target.value })} />
          <Field label="Marks out of" name="emax" type="number" min="1" required value={ef.max_score} onChange={(e) => setEf({ ...ef, max_score: e.target.value })} />
          <Button block onClick={createExam}>Create exam</Button>
        </Modal>
      )}
    </div>
  );
}
