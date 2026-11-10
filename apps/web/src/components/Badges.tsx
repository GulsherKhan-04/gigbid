export function FitBar({ fit }: { fit?: number | null }) {
  if (fit == null) return <span className="fit-label">Not scored yet</span>;
  const pct = Math.round(fit * 100);
  return (
    <div className="fit" aria-label={`Fit ${pct} percent`}>
      <div className="fit-track"><div className="fit-fill" style={{ width: `${pct}%` }} /></div>
      <span className="fit-label num">Fit {pct}%</span>
    </div>
  );
}

const ACTION: Record<string, string> = { bid: "Bid", watch: "Watch", skip: "Skip" };
export function ActionBadge({ action, status }: { action?: string | null; status?: string | null }) {
  if (status === "awaiting_approval") return <span className="badge bid">Needs your approval</span>;
  if (status === "submitted") return <span className="badge neutral">Submitted</span>;
  if (status === "marketplace_unavailable") return <span className="badge risk">Waiting for marketplace</span>;
  if (status === "dead_letter" || status === "needs_attention") return <span className="badge risk">Needs attention</span>;
  if (!action) return <span className="badge neutral">{status === "queued" ? "Queued" : "Analysing"}</span>;
  return <span className={`badge ${action}`}>{ACTION[action] ?? action}</span>;
}

const FLAG: Record<string, string> = {
  scam: "Likely scam", free_work: "Free work request", off_platform: "Off-platform ask", injection: "Hidden instructions",
  low_budget: "Low budget", unverified_payment: "Payment unverified", new_client: "New client", vague: "Vague brief",
};
export function RiskFlags({ flags }: { flags?: string[] | null }) {
  if (!flags?.length) return <span className="badge neutral">No risks found</span>;
  return <span className="flags">{flags.map((f) => <span key={f} className="badge risk">{FLAG[f] ?? f}</span>)}</span>;
}
