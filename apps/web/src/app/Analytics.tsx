import { ErrorBox, Loading } from "../components/States";
import { useQuery } from "../lib/hooks";

type A = { jobs_analysed: number; proposals_sent: number; connects_spent: number; p50_seconds: number | null; p95_seconds: number | null;
  avg_cost_usd: number | null; by_category: Record<string, { sent: number; replied: number; hired: number; connects: number }>; skip_reasons: Record<string, number> };

export default function Analytics() {
  const { data, error, loading, reload } = useQuery<A>("/api/analytics");
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} retry={reload} />;
  const pct = (a: number, b: number) => (b ? `${Math.round((a / b) * 100)}%` : "–");
  return (
    <>
      <div className="page-head"><div><h1>Analytics</h1><p>What your Connects bought, and what GigBid cost to run.</p></div></div>
      <div className="stats">
        <div className="stat"><b className="num">{data.jobs_analysed}</b><span>jobs analysed</span></div>
        <div className="stat"><b className="num">{data.proposals_sent}</b><span>proposals sent</span></div>
        <div className="stat"><b className="num">{data.connects_spent}</b><span>Connects spent</span></div>
        <div className="stat"><b className="num">{data.p95_seconds?.toFixed(1) ?? "–"}s</b><span>p95 time per job</span></div>
        <div className="stat"><b className="num">{data.avg_cost_usd != null ? `$${data.avg_cost_usd.toFixed(4)}` : "–"}</b><span>model cost per job</span></div>
      </div>
      <div className="grid-2">
        <section className="panel"><h2>Reply and hire rate by category</h2>
          <table className="matrix"><thead><tr><th>Category</th><th>Sent</th><th>Reply rate</th><th>Hire rate</th><th>Connects</th></tr></thead>
            <tbody>{Object.entries(data.by_category).map(([c, v]) => (
              <tr key={c}><td>{c}</td><td className="num">{v.sent}</td><td className="num">{pct(v.replied, v.sent)}</td><td className="num">{pct(v.hired, v.sent)}</td><td className="num">{v.connects}</td></tr>
            ))}</tbody></table>
          {!Object.keys(data.by_category).length && <p className="muted">Send a proposal to start tracking outcomes.</p>}
        </section>
        <section className="panel"><h2>Top skip reasons</h2>
          {Object.entries(data.skip_reasons).sort((a, b) => b[1] - a[1]).map(([r, n]) => <p key={r}><b className="num">{n}</b> {r}</p>)}
          {!Object.keys(data.skip_reasons).length && <p className="muted">No skipped jobs yet.</p>}
        </section>
      </div>
    </>
  );
}
