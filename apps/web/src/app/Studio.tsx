import { useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import ApprovalPanel from "../components/ApprovalPanel";
import EvidenceLetter from "../components/EvidenceHover";
import RunTimeline from "../components/RunTimeline";
import { Empty, ErrorBox, Loading } from "../components/States";
import { useQuery } from "../lib/hooks";
import type { Detail } from "./types";

export default function Studio() {
  const { id } = useParams();
  const { data, error, loading, reload } = useQuery<Detail>(`/api/jobs/${id}`);
  const refresh = useCallback(() => void reload(), [reload]);
  if (loading && !data) return <Loading rows={8} />;
  if (error || !data) return <ErrorBox message={error ?? "Not found"} retry={reload} />;
  const s = data.state;
  const d = s.proposal_draft;
  const pending = s.pending_approval[0];
  const evidence = pending?.evidence ?? Object.fromEntries((s.evidence ?? []).map((e) => [e.evidence_id, e]));
  const lastCritique = s.critiques?.[s.critiques.length - 1];

  if (!d) return <Empty title="No draft yet"><p>GigBid drafts a proposal only for jobs it recommends bidding on. <Link to={`/jobs/${id}`}>See the analysis</Link>.</p></Empty>;

  return (
    <>
      <div className="page-head">
        <div><h1>{s.job?.title ?? data.row.title}</h1>
          <p>{pending ? "Read it, check the evidence behind each highlighted claim, then approve, edit or reject."
            : s.status === "submitted" ? "Sent to the marketplace as a draft." : s.status === "rejected" ? "You rejected this draft." : "Working…"}</p></div>
        <Link to={`/jobs/${id}`} className="muted">Back to analysis</Link>
      </div>
      <div className="studio">
        <div>
          <EvidenceLetter text={d.cover_letter} claims={d.claims ?? []} evidence={evidence} />
          {d.screening_answers?.length > 0 && (
            <section className="panel" style={{ marginTop: 18 }}><h2>Screening answers</h2>
              {s.job_spec?.screening_questions.map((q, i) => <div key={i} style={{ marginBottom: 12 }}><b>{q}</b><p>{d.screening_answers[i]}</p></div>)}
            </section>
          )}
          {pending && <ApprovalPanel key={d.cover_letter} endpoint={`/api/approvals/${id}`} draft={d.cover_letter} preview={pending.dry_run} onDone={refresh} />}
        </div>
        <aside className="notes">
          <section className="panel">
            <h2>Checks</h2>
            <div className="notes">
              <div className={`note ${d.unsupported_removed?.length ? "compliance" : "ok"}`}>
                {d.unsupported_removed?.length ? <>Removed {d.unsupported_removed.length} claim{d.unsupported_removed.length > 1 ? "s" : ""} your portfolio doesn’t support:
                  {d.unsupported_removed.map((c, i) => <div key={i} className="removed">{c}</div>)}</> : "Every claim is backed by your portfolio."}
              </div>
              <div className={`note ${lastCritique?.passed ? "ok" : "critic"}`}>
                Reviewer {lastCritique?.passed ? "approved the draft" : "still had notes"} after {d.revision} revision{d.revision === 1 ? "" : "s"}.
                {!lastCritique?.passed && lastCritique?.reasons.map((r, i) => <div key={i}>{r}</div>)}
              </div>
              <div className={`note ${s.compliance_verdict?.violations.length ? "compliance" : "ok"}`}>
                {s.compliance_verdict?.violations.length ? <>Platform rules fixed:{s.compliance_verdict.violations.map((v, i) => <div key={i}>{v}</div>)}</> : "Follows platform rules."}
              </div>
            </div>
          </section>
          <section className="panel"><h2>Progress</h2><RunTimeline channel={`/api/jobs/${id}/stream`} onDone={refresh} /></section>
        </aside>
      </div>
    </>
  );
}
