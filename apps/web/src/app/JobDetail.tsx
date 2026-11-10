import { useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import { ActionBadge, FitBar, RiskFlags } from "../components/Badges";
import RunTimeline from "../components/RunTimeline";
import { ErrorBox, Loading } from "../components/States";
import { api } from "../lib/api/client";
import { useQuery } from "../lib/hooks";
import type { Detail } from "./types";

export default function JobDetail() {
  const { id } = useParams();
  const { data, error, loading, reload } = useQuery<Detail>(`/api/jobs/${id}`);
  const done = useCallback(() => void reload(), [reload]);
  if (loading && !data) return <Loading rows={6} />;
  if (error || !data) return <ErrorBox message={error ?? "Not found"} retry={reload} />;
  const { state: s, row } = data;
  const ev = Object.fromEntries((s.evidence ?? []).map((e) => [e.evidence_id, e]));

  return (
    <>
      <div className="page-head">
        <div><h1>{s.job?.title ?? row.title}</h1>
          <p><ActionBadge action={s.decision?.action} status={s.pending_approval.length ? "awaiting_approval" : s.status} /> {s.decision?.reason}</p></div>
        <div className="row" style={{ flex: "0 0 auto" }}>
          <Link to={`/runs/${id}`} className="btn-quiet" style={{ padding: ".55em 1em", textDecoration: "none", borderRadius: 6 }}>View run</Link>
          {s.pending_approval.length > 0
            ? <Link to={`/studio/${id}`} className="btn-primary" style={{ padding: ".55em 1em", textDecoration: "none", borderRadius: 6 }}>Open proposal</Link>
            : <button className="btn-quiet" onClick={() => api(`/api/jobs/${id}/analyse`, { method: "POST" }).then(reload)}>Analyse again</button>}
        </div>
      </div>
      <div className="grid-2">
        <div>
          <section className="panel">
            <h2>Requirements and your evidence</h2>
            {s.fit_report ? (
              <div style={{ overflowX: "auto" }}>
                <table className="matrix">
                  <thead><tr><th>The client needs</th><th>Proof from your portfolio</th><th>Match</th></tr></thead>
                  <tbody>{s.fit_report.matrix.map((m, i) => (
                    <tr key={i}><td>{m.requirement}</td>
                      <td>{m.evidence_ids.length ? m.evidence_ids.map((e) => <div key={e}>{ev[e]?.title || ev[e]?.project || e}</div>) : <span className="muted">Nothing found</span>}</td>
                      <td className={`strength-${m.strength}`}>{m.strength === "none" ? "Gap" : m.strength === "strong" ? "Strong" : "Partial"}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            ) : <p className="muted">Fit not analysed yet.</p>}
            {s.fit_report && <div style={{ marginTop: 14 }}><FitBar fit={s.fit_report.score} />{s.fit_report.reasons.map((r, i) => <p key={i} style={{ marginTop: 8 }}>{r}</p>)}</div>}
          </section>
          <section className="panel">
            <h2>What the client asked for</h2>
            {s.job_spec ? <>
              <h3>Deliverables</h3><ul>{s.job_spec.deliverables.map((d, i) => <li key={i}>{d}</li>)}</ul>
              {s.job_spec.hidden_needs.length > 0 && <><h3>Likely unstated needs</h3><ul>{s.job_spec.hidden_needs.map((d, i) => <li key={i}>{d}</li>)}</ul></>}
              {s.job_spec.screening_questions.length > 0 && <><h3>Screening questions</h3><ul>{s.job_spec.screening_questions.map((d, i) => <li key={i}>{d}</li>)}</ul></>}
            </> : <p className="muted">{s.job?.description}</p>}
          </section>
        </div>
        <aside>
          <section className="panel">
            <h2>Risk</h2>
            <RiskFlags flags={s.risk_report?.flags} />
            <p style={{ marginTop: 10 }}>{s.risk_report?.explanation}</p>
            {!!s.risk_report?.injected_instructions?.length && (
              <div className="note compliance"><b>Ignored hidden instructions in the post:</b>{s.risk_report.injected_instructions.map((t, i) => <div key={i}>“{t}”</div>)}</div>
            )}
          </section>
          <section className="panel">
            <h2>Price</h2>
            {s.price_quote ? <dl className="kv">
              <dt>Suggested bid</dt><dd className="num">${s.price_quote.amount_usd} {s.price_quote.rate_type}</dd>
              <dt>Connects</dt><dd className="num">{s.price_quote.connects_cost}{s.price_quote.worth_connects ? "" : " (not worth it)"}</dd>
            </dl> : <p className="muted">Priced only when GigBid recommends a bid.</p>}
            {s.price_quote && <p className="muted" style={{ marginTop: 10 }}>{s.price_quote.rationale}</p>}
          </section>
          <section className="panel"><h2>Live progress</h2><RunTimeline channel={`/api/jobs/${id}/stream`} onDone={done} /></section>
          {!!s.errors?.length && <section className="panel"><h2>Problems</h2>{s.errors.map((e, i) => <p key={i} className="error">{e}</p>)}</section>}
        </aside>
      </div>
    </>
  );
}
