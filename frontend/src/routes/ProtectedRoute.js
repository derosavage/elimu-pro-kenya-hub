import { Navigate, Outlet } from 'react-router-dom';
import { useAuth, homeFor } from '../context/AuthContext';
import { Loading } from '../components/ui';

export default function ProtectedRoute({ roles }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading label="Loading your account..." />;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={homeFor(user)} replace />;
  return <Outlet />;
}
