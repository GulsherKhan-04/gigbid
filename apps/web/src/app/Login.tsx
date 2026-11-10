import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, auth, type Session } from "../lib/api/client";

const PERSONA_LABEL = (p: string) => p.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export default function Login() {
  const nav = useNavigate();
  const [tab, setTab] = useState<"in" | "up">("in");
  const [personas, setPersonas] = useState<string[]>([]);
  const [f, setF] = useState({ email: "", password: "", persona: "", hourly: 30, floor: 200, connects: 80, searches: "python, machine learning" });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api<string[]>("/api/personas").then((p) => { setPersonas(p); setF((x) => ({ ...x, persona: p[0] ?? "" })); }).catch(() => {}); }, []);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      const s = tab === "in"
        ? await api<Session>("/api/auth/login", { method: "POST", json: { email: f.email, password: f.password } })
        : await api<Session>("/api/auth/signup", { method: "POST", json: {
            email: f.email, password: f.password, persona: f.persona, hourly_rate_usd: +f.hourly,
            minimum_project_budget_usd: +f.floor, weekly_connects_budget: +f.connects,
            saved_searches: f.searches.split(",").map((s) => s.trim()).filter(Boolean) } });
      auth.set(s.token); nav("/inbox");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <div className="auth">
      <section className="auth-art">
        <h1>Bid on the work you can prove.</h1>
        <p>GigBid reads new jobs, flags the risky ones and drafts proposals where every claim points to your own work. Nothing is sent until you approve it.</p>
        <div className="specimen" aria-hidden="true">
          Your churn model needs honest evaluation on imbalanced data.{" "}
          <mark className="claim">I compared logistic regression and random forest on a similar dataset</mark>{" "}
          and reported precision and recall per class. Which metric matters most to your team?
        </div>
      </section>
      <form className="auth-form" onSubmit={submit}>
        <div className="tabs" role="tablist">
          <button type="button" role="tab" aria-selected={tab === "in"} onClick={() => setTab("in")}>Sign in</button>
          <button type="button" role="tab" aria-selected={tab === "up"} onClick={() => setTab("up")}>Create account</button>
        </div>
        <label>Email<input type="email" autoComplete="email" required value={f.email} onChange={set("email")} /></label>
        <label>Password<input type="password" autoComplete={tab === "in" ? "current-password" : "new-password"} minLength={8} required value={f.password} onChange={set("password")} /></label>
        {tab === "up" && <>
          <label>Portfolio
            <select value={f.persona} onChange={set("persona")} required>
              {personas.map((p) => <option key={p} value={p}>{PERSONA_LABEL(p)}</option>)}
            </select>
          </label>
          <div className="row">
            <label>Hourly rate (USD)<input type="number" min={5} value={f.hourly} onChange={set("hourly")} /></label>
            <label>Lowest project you take (USD)<input type="number" min={0} value={f.floor} onChange={set("floor")} /></label>
          </div>
          <label>Weekly Connects budget<input type="number" min={0} value={f.connects} onChange={set("connects")} /></label>
          <label>Saved searches (comma separated)<input value={f.searches} onChange={set("searches")} /></label>
          <p className="muted" style={{ margin: 0 }}>You can connect Upwork and upload more work later in Settings.</p>
        </>}
        {err && <div className="error" role="alert">{err}</div>}
        <button className="btn-primary" disabled={busy}>{tab === "in" ? "Sign in" : "Create account"}</button>
      </form>
    </div>
  );
}
