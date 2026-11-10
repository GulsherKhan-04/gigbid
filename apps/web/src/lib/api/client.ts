// Typed wrapper over the schema generated from FastAPI's OpenAPI (src/lib/api/schema.ts, do not hand-edit it).
import type { components, paths } from "./schema";

export type JobRow = components["schemas"]["JobRow"];
export type Approval = components["schemas"]["Approval"];
export type SignUp = components["schemas"]["SignUp"];
export type SettingsBody = components["schemas"]["Settings"];
export type Session = components["schemas"]["Session"];
type Path = keyof paths;

const TOKEN = "gigbid.token";
export const auth = {
  get: () => localStorage.getItem(TOKEN),
  set: (t: string) => localStorage.setItem(TOKEN, t),
  clear: () => localStorage.removeItem(TOKEN),
};

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function api<T = unknown>(path: Path | string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = { "x-trace-id": crypto.randomUUID().replace(/-/g, "") };
  const token = auth.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init.json !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(path, { ...init, headers, body: init.json !== undefined ? JSON.stringify(init.json) : init.body });
  if (res.status === 401) { auth.clear(); if (!location.pathname.startsWith("/login")) location.assign("/login"); }
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* not json */ }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export function stream(path: string, onEvent: (e: RunEvent) => void): () => void {
  const es = new EventSource(`${path}?token=${encodeURIComponent(auth.get() ?? "")}`);
  es.onmessage = (m) => onEvent(JSON.parse(m.data));
  return () => es.close();
}

export type RunEvent = {
  type: "run_started" | "node" | "interrupt" | "error" | "run_finished";
  node?: string; status?: string | null; error?: string; elapsed?: number; trace_id?: string;
  trace?: { seconds?: number; usd?: number; model?: string; summary?: string };
};
