import { useCallback } from "react";
import { useParams } from "react-router-dom";
import RunTimeline from "../components/RunTimeline";
import { ErrorBox, Loading } from "../components/States";
import { api } from "../lib/api/client";
import { useQuery } from "../lib/hooks";
import type { JobState } from "./types";

type Hist = { checkpoint_id: string; next: string[]; status?: string; steps?: number; created_at: string }[];

export default function RunViewer() {
  const { id } = useParams();
  const trace = useQuery<{ trace: JobState["trace"]; usage: JobState["usage"]; errors: string[] }>(`/api/runs/${id}/trace`);
  const hist = useQuery<Hist>(`/api/runs/${id}/history`);
  const refresh = useCallback(() => { void trace.reload(); void hist.reload(); }, [trace, hist]);
  if (trace.loading && !trace.data) return <Loading rows={6} />;
  if (trace.error) return <ErrorBox message={trace.error} retry={trace.reload} />;
  const usage = Object.values(trace.data?.usage ?? {});
  const usd = usage.reduce((a, u) => a + (u.usd ?? 0), 0);
  const tokens = usage.reduce((a, u) => a + (u.prompt_tokens ?? 0) + (u.completion_tokens ?? 0), 0);
  const ls = import.meta.env.VITE_TRACE_URL as string | undefined;
  return (
    <>
      <div className="page-head"><div><h1>Agent run</h1><p>Every step, its model, tokens, cost and time.</p></div>
        {ls && <a href={ls} target="_blank" rel="noreferrer">Open full trace</a>}</div>
      <div className="stats">
        <div className="stat"><b className="num">{tokens.toLocaleString()}</b><span>tokens</span></div>
        <div className="stat"><b className="num">${usd.toFixed(4)}</b><span>model cost</span></div>
        <div className="stat"><b className="num">{trace.data?.trace?.length ?? 0}</b><span>steps</span></div>
      </div>
      <div className="grid-2">
        <section className="panel"><h2>Steps</h2>
          <table className="matrix"><thead><tr><th>Node</th><th>Model</th><th>Tokens</th><th>Cost</th><th>Time</th></tr></thead>
            <tbody>{trace.data?.trace?.map((t, i) => (
              <tr key={i}><td>{t.node}</td><td className="muted">{t.model ?? "rules"}</td>
                <td className="num">{(t.prompt_tokens ?? 0) + (t.completion_tokens ?? 0) || "–"}</td>
                <td className="num">{t.usd ? `$${t.usd.toFixed(5)}` : "–"}</td><td className="num">{t.seconds?.toFixed(2) ?? "–"}s</td></tr>
            ))}</tbody></table>
        </section>
        <aside>
          <section className="panel"><h2>Live</h2><RunTimeline channel={`/api/jobs/${id}/stream`} onDone={refresh} /></section>
          <section className="panel"><h2>Checkpoints</h2>
            <p className="muted">Replay the job from any saved step.</p>
            {hist.data?.slice(0, 12).map((h) => (
              <div key={h.checkpoint_id} className="row" style={{ alignItems: "center", marginBottom: 6 }}>
                <span>{h.next.join(", ") || "end"} <span className="muted">step {h.steps ?? 0}</span></span>
                {h.next.length > 0 && <button className="chip" style={{ flex: "0 0 auto" }} onClick={() => api(`/api/runs/${id}/replay/${h.checkpoint_id}`, { method: "POST" })}>Replay from here</button>}
              </div>
            ))}
          </section>
        </aside>
      </div>
    </>
  );
}
