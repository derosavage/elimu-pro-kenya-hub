import { Link } from 'react-router-dom';
import { useFetch } from '../../hooks/useFetch';
import { Alert, ErrorState, Loading } from '../../components/ui';
import { money } from '../../utils/format';

export default function AdminDashboard() {
  const { data: o, loading, error, reload } = useFetch('/schools/overview');
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const stat = (label, value, to) => (
    <div className="card stat"><div className="label">{label}</div><div className="value">{value}</div>{to && <Link to={to} className="small">Open</Link>}</div>
  );
  return (
    <div className="stack">
      <div><h1>{o.school.name}</h1><p className="muted">{o.current_term ? `${o.current_term.name}, ${o.current_term.year}` : 'No current term set'}</p></div>
      {o.is_demo && <Alert type="info">This school contains <b>demo data</b> for development. Do not use it in production.</Alert>}
      <div className="cards">
        {stat('Total students', o.total_students, '/admin/students')}{stat('Active students', o.active_students)}
        {stat('New applications', o.new_applications, '/admin/applications')}{stat('Pending review', o.pending_applications, '/admin/applications')}
      </div>
      <h2>Fees this term</h2>
      <div className="cards">
        {stat('Expected', money(o.fees_expected))}{stat('Collected', money(o.fees_collected))}{stat('Outstanding', money(o.fees_outstanding), '/admin/fees')}
      </div>
    </div>
  );
}
