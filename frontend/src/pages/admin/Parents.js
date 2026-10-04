import { Link } from 'react-router-dom';
import { useFetch } from '../../hooks/useFetch';
import { Empty, ErrorState, Loading } from '../../components/ui';

export default function Parents() {
  const { data, loading, error, reload } = useFetch('/parents');
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="stack">
      <h1>Parents & guardians</h1>
      <p className="muted small">Parent logins are created from a student's page: open the student, then choose "Create login" next to a guardian.</p>
      {data.length === 0 ? <div className="card"><Empty title="No parent logins yet">Open a student and create a login for their guardian.</Empty></div> : (
        <div className="list">{data.map((p) => (
          <div key={p.id} className="list-row" style={{ alignItems: 'flex-start' }}>
            <div className="grow"><b>{p.full_name}</b> {!p.is_active && <span className="badge red">Inactive</span>}
              <div className="small muted">{p.email}{p.phone ? ` · ${p.phone}` : ''}</div></div>
            <div className="right small">{p.children.map((c) => <div key={c.id}><Link to={`/admin/students/${c.id}`}>{c.full_name}</Link> <span className="muted">({c.class})</span></div>)}</div>
          </div>))}</div>
      )}
    </div>
  );
}
