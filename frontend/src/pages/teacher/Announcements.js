import { useFetch } from '../../hooks/useFetch';
import { Empty, ErrorState, Loading } from '../../components/ui';
import { fmtDate } from '../../utils/format';

export default function TeacherAnnouncements() {
  const { data, loading, error, reload } = useFetch('/teacher/announcements');
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="stack"><h1>Announcements</h1>
      {data.length === 0 ? <div className="card"><Empty title="No announcements yet" /></div> : data.map((a) => (
        <div key={a.id} className={`card prio-${a.priority}`}><strong>{a.title}</strong><p className="small muted">{fmtDate(a.created_at)} · {a.author}</p><p>{a.content}</p></div>))}
    </div>
  );
}
