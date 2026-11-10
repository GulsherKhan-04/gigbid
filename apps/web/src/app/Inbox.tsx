import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ActionBadge, FitBar, RiskFlags } from "../components/Badges";
import { Empty, ErrorBox, Loading } from "../components/States";
import { api, type JobRow } from "../lib/api/client";
import { useQuery } from "../lib/hooks";

const FILTERS = [["all", "All"], ["bid", "Worth bidding"], ["approval", "Needs approval"], ["skip", "Skipped"]] as const;

export default function Inbox() {
  const { data, error, loading, reload } = useQuery<JobRow[]>("/api/jobs");
  const [filter, setFilter] = useState<(typeof FILTERS)[number][0]>("all");
  const [scouting, setScouting] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const rows = useMemo(() => (data ?? []).filter((r) =>
    filter === "all" || (filter === "approval" ? r.status === "awaiting_approval" : r.action === filter)), [data, filter]);

  const scout = async () => {
    setScouting(true); setMsg(null);
    try {
      const r = await api<{ queued: string[] }>("/api/jobs/scout", { method: "POST" });
      setMsg(r.queued.length ? `Found ${r.queued.length} new job${r.queued.length > 1 ? "s" : ""}. Analysing now.` : "No new jobs since the last check.");
      const t = setInterval(reload, 2500); setTimeout(() => clearInterval(t), 60000);
    } catch (e) { setMsg((e as Error).message); } finally { setScouting(false); }
  };

  return (
    <>
      <div className="page-head">
        <div><h1>Inbox</h1><p>New jobs from your saved searches, best fit first.</p></div>
        <button className="btn-primary" onClick={scout} disabled={scouting}>{scouting ? "Checking…" : "Check for new jobs"}</button>
      </div>
      {msg && <p role="status" className="muted">{msg}</p>}
      <div className="filters" role="group" aria-label="Filter jobs" style={{ marginBottom: 14 }}>
        {FILTERS.map(([k, label]) => <button key={k} className="chip" aria-pressed={filter === k} onClick={() => setFilter(k)}>{label}</button>)}
      </div>
      {loading && !data ? <Loading /> : error ? <ErrorBox message={error} retry={reload} /> : rows.length === 0 ? (
        <Empty title={data?.length ? "Nothing in this view" : "Your inbox is empty"}>
          <p>{data?.length ? "Try another filter." : "Check for new jobs to run your saved searches now. GigBid also checks on a schedule."}</p>
        </Empty>
      ) : (
        <div className="ledger">
          {rows.map((r) => (
            <Link key={r.job_id} to={r.status === "awaiting_approval" ? `/studio/${r.job_id}` : `/jobs/${r.job_id}`} className="ledger-row">
              <div style={{ minWidth: 0 }}>
                <div className="title">{r.title ?? r.job_id}</div>
                <div className="sub">{r.reason ?? (r.category ? `Category: ${r.category}` : "Waiting for analysis")}</div>
              </div>
              <div className="col-hide"><FitBar fit={r.fit} /></div>
              <div className="col-hide num">{r.price ? `$${Math.round(r.price)}` : "–"}<div className="sub">{r.connects ?? "–"} Connects</div></div>
              <div className="col-hide"><RiskFlags flags={r.flags?.filter((f) => ["scam", "free_work", "off_platform", "injection"].includes(f))} /></div>
              <div style={{ justifySelf: "end" }}><ActionBadge action={r.action} status={r.status} /></div>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
