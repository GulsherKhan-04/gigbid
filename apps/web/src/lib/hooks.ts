import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";

export function useQuery<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!!path);
  const load = useCallback(async () => {
    if (!path) return;
    setLoading(true);
    try { setData(await api<T>(path)); setError(null); }
    catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);
  useEffect(() => { void load(); }, [load]);
  return { data, error, loading, reload: load, setData };
}

export function useHealth() {
  const [degraded, setDegraded] = useState<string[]>([]);
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const h = await api<{ mcp: Record<string, boolean> }>("/api/health");
        if (alive) setDegraded(Object.entries(h.mcp).filter(([, ok]) => !ok).map(([k]) => k));
      } catch { if (alive) setDegraded(["api"]); }
    };
    void tick();
    const t = setInterval(tick, 15000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  return degraded;
}
