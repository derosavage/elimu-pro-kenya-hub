import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useFetch } from '../../hooks/useFetch';
import { ErrorState, Loading } from '../../components/ui';
import { Fees, Results, Timetable } from '../student/Pages';
import { initials } from '../../utils/format';

const TABS = [['results', 'Results'], ['fees', 'Fees'], ['timetable', 'Timetable']];

export default function ParentChild() {
  const { id } = useParams();
  const child = useFetch(`/parent/children/${id}`);
  const [tab, setTab] = useState('results');
  if (child.loading) return <Loading />;
  if (child.error) return <ErrorState error={child.error} onRetry={child.reload} />;
  const c = child.data;
  const base = `/parent/children/${id}`;
  return (
    <div className="stack">
      <Link to="/parent" className="small no-print">← My children</Link>
      <div className="greet">
        <div className="avatar" style={{ width: 56, height: 56 }}>{initials(c.full_name)}</div>
        <div><h1>{c.full_name}</h1>
          <div className="small muted">{c.class}{c.stream ? ` ${c.stream}` : ''} · Adm No. {c.admission_number}</div>
          {c.status !== 'active' && <span className="badge">{c.status}</span>}</div>
      </div>
      <div className="tabs no-print">{TABS.map(([k, l]) => <button key={k} className={`tab ${tab === k ? 'active' : ''}`} onClick={() => setTab(k)}>{l}</button>)}</div>
      {tab === 'results' && <Results key={`r${id}`} base={base} title="" />}
      {tab === 'fees' && <Fees key={`f${id}`} base={base} title="" />}
      {tab === 'timetable' && <Timetable key={`t${id}`} base={base} title="" />}
    </div>
  );
}
