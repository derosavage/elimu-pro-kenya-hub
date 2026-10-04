import { useFetch } from '../../hooks/useFetch';
import { Empty, ErrorState, Loading } from '../../components/ui';
import { fmtDate } from '../../utils/format';

export default function ParentAnnouncements() {
  const { data, loading, error, reload } = useFetch('/parent/announcements');
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="stack"><h1>School news</h1>
      {data.length === 0 ? <div className="card"><Empty title="No announcements yet" /></div> : data.map((a) => (
        <div key={a.id} className={`card prio-${a.priority}`}><div className="row between"><strong>{a.title}</strong>{a.priority !== 'normal' && <span className={`badge ${a.priority === 'urgent' ? 'red' : 'gold'}`}>{a.priority}</span>}</div>
          <p className="small muted">{fmtDate(a.created_at)} · {a.author}</p><p>{a.content}</p></div>))}
    </div>
  );
}
