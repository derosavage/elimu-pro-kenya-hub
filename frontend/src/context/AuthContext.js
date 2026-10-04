import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api, tokenStore } from '../services/api';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!tokenStore.get());

  const logout = useCallback(() => { tokenStore.clear(); setUser(null); }, []);

  const refresh = useCallback(async () => {
    try {
      const res = await api.get('/auth/me');
      setUser(res.data);
      return res.data;
    } catch (e) {
      if (e.status === 401 || e.status === 403) logout();
      return null;
    } finally { setLoading(false); }
  }, [logout]);

  useEffect(() => { if (tokenStore.get()) refresh(); }, [refresh]);
  useEffect(() => {
    window.addEventListener('elimupro:unauthorized', logout);
    return () => window.removeEventListener('elimupro:unauthorized', logout);
  }, [logout]);

  const startSession = async (path, body) => {
    const res = await api.post(path, body);
    tokenStore.set(res.data.token);
    return refresh();
  };

  return (
    <AuthContext.Provider value={{ user, loading, logout, refresh,
      login: (email, password) => startSession('/auth/login', { email, password }),
      register: (payload) => startSession('/auth/register', payload) }}>
      {children}
    </AuthContext.Provider>
  );
}

export const homeFor = (user) => {
  if (!user) return '/login';
  if (user.role === 'student') return user.is_enrolled ? '/student' : '/student/application';
  if (user.role === 'super_admin') return '/platform';
  if (user.role === 'parent') return '/parent';
  if (user.role === 'teacher' || user.role === 'class_teacher') return '/teacher';
  if (user.role === 'bursar') return '/admin/fees';
  return '/admin';
};
