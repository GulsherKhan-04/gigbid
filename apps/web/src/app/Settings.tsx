import { useEffect, useState } from "react";
import { Empty, ErrorBox, Loading } from "../components/States";
import { api, auth } from "../lib/api/client";
import { useQuery } from "../lib/hooks";

type Me = { email: string; persona: string; profile: { autonomy?: string; hourly_rate_usd?: number; minimum_project_budget_usd?: number; weekly_connects_budget?: number; saved_searches?: string[] } };
type Mem = { kind: string; key: string; rule?: string; insight?: string; evidence_edits?: number }[];

export default function Settings() {
  const me = useQuery<Me>("/api/auth/me");
  const mem = useQuery<Mem>("/api/memory");
  const acc = useQuery<{ gigsim: boolean; upwork: boolean }>("/api/accounts");
  const [f, setF] = useState({ autonomy: "suggest_only", hourly: 30, floor: 200, connects: 80, searches: "" });
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => {
    const p = me.data?.profile; if (!p) return;
    setF({ autonomy: p.autonomy ?? "suggest_only", hourly: p.hourly_rate_usd ?? 30, floor: p.minimum_project_budget_usd ?? 200,
      connects: p.weekly_connects_budget ?? 80, searches: (p.saved_searches ?? []).join(", ") });
  }, [me.data]);
  if (me.loading && !me.data) return <Loading />;
  if (me.error) return <ErrorBox message={me.error} retry={me.reload} />;

  const save = async () => {
    await api("/api/settings", { method: "PUT", json: { autonomy: f.autonomy, hourly_rate_usd: +f.hourly, minimum_project_budget_usd: +f.floor,
      weekly_connects_budget: +f.connects, saved_searches: f.searches.split(",").map((s) => s.trim()).filter(Boolean) } });
    setMsg("Settings saved.");
  };
  const connectUpwork = async () => {
    try { const r = await api<{ url: string }>("/api/oauth/upwork/start"); location.assign(r.url); }
    catch (e) { setMsg((e as Error).message); }
  };

  return (
    <>
      <div className="page-head"><div><h1>Settings</h1><p>Signed in as {me.data?.email}</p></div>
        <button className="btn-quiet" onClick={() => { auth.clear(); location.assign("/login"); }}>Sign out</button></div>
      <div className="grid-2">
        <div>
          <section className="panel"><h2>How much GigBid may do</h2>
            <label><select value={f.autonomy} onChange={(e) => setF({ ...f, autonomy: e.target.value })}>
              <option value="suggest_only">Suggest everything, I decide</option>
              <option value="auto_skip_low_fit">Skip clearly poor fits for me</option>
            </select></label>
            <p className="muted" style={{ marginTop: 8 }}>GigBid never sends a proposal or message without your approval, at any setting.</p>
          </section>
          <section className="panel"><h2>Rates, budget and searches</h2>
            <div className="row">
              <label>Hourly rate (USD)<input type="number" value={f.hourly} onChange={(e) => setF({ ...f, hourly: +e.target.value })} /></label>
              <label>Lowest project (USD)<input type="number" value={f.floor} onChange={(e) => setF({ ...f, floor: +e.target.value })} /></label>
              <label>Weekly Connects<input type="number" value={f.connects} onChange={(e) => setF({ ...f, connects: +e.target.value })} /></label>
            </div>
            <label style={{ marginTop: 12 }}>Saved searches<input value={f.searches} onChange={(e) => setF({ ...f, searches: e.target.value })} /></label>
            <div className="row" style={{ marginTop: 14, alignItems: "center" }}>
              <button className="btn-primary" style={{ flex: "0 0 auto" }} onClick={save}>Save settings</button>
              {msg && <span role="status">{msg}</span>}
            </div>
          </section>
          <section className="panel"><h2>Connected accounts</h2>
            <p>GigSim marketplace: <b>{acc.data?.gigsim ? "connected" : "not connected"}</b></p>
            <p>Upwork: <b>{acc.data?.upwork ? "connected" : "not connected"}</b></p>
            {!acc.data?.upwork && <button className="btn-quiet" onClick={connectUpwork}>Connect Upwork</button>}
            <p className="muted" style={{ marginTop: 10 }}>Portfolio: {me.data?.persona}. <button className="chip" onClick={() => api<{ chunks: number }>("/api/portfolio/reindex", { method: "POST" }).then((r) => setMsg(`Re-indexed ${r.chunks} portfolio pieces.`))}>Re-index portfolio</button></p>
          </section>
        </div>
        <section className="panel"><h2>What GigBid has learned</h2>
          <p className="muted">Learned only after the same pattern shows up in at least three of your edits, or three outcomes in a category.</p>
          {mem.loading ? <Loading rows={2} /> : !mem.data?.length ? <Empty title="Nothing learned yet"><p>Edit a few drafts and GigBid will pick up your style.</p></Empty> :
            mem.data.map((m) => (
              <div key={m.kind + m.key} className="row" style={{ alignItems: "center", borderTop: "1px solid var(--line)", padding: "10px 0" }}>
                <span><span className="badge neutral">{m.kind === "style" ? "Style" : "Outcome"}</span> {m.rule ?? m.insight}</span>
                <button className="btn-danger" style={{ flex: "0 0 auto" }} onClick={() => api(`/api/memory/${m.kind}/${encodeURIComponent(m.key)}`, { method: "DELETE" }).then(mem.reload)}>Forget</button>
              </div>
            ))}
        </section>
      </div>
    </>
  );
}
