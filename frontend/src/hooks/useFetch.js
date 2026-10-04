import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';

export function useFetch(path) {
  const [state, setState] = useState({ data: null, meta: null, loading: !!path, error: null });
  const load = useCallback(async () => {
    if (!path) return;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const res = await api.get(path);
      setState({ data: res.data, meta: res.meta || null, loading: false, error: null });
    } catch (e) {
      setState({ data: null, meta: null, loading: false, error: e });
    }
  }, [path]);
  useEffect(() => { load(); }, [load]);
  return { ...state, reload: load };
}
