import { useState } from "react";
import { api } from "../lib/api/client";

type Preview = { dry_run?: boolean; preview?: { bid_amount_usd?: number; connects_cost?: number; rate_type?: string } };

/** Approve, edit (diffed, saved for style memory, re-checked by Compliance) or reject with a reason. */
export default function ApprovalPanel({ endpoint, draft, preview, onDone }: { endpoint: string; draft: string; preview?: Preview; onDone: () => void }) {
  const [mode, setMode] = useState<"view" | "edit" | "reject">("view");
  const [text, setText] = useState(draft);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const p = preview?.preview;

  const send = async (body: object) => {
    setBusy(true); setErr(null);
    try { await api(endpoint, { method: "POST", json: body }); onDone(); }
    catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  };

  return (
    <>
      {mode === "edit" && (
        <label style={{ marginTop: 18 }}>Edit the proposal
          <textarea data-testid="edit-box" value={text} onChange={(e) => setText(e.target.value)} rows={12} />
          <span className="muted" style={{ fontWeight: 400 }}>Your edit is re-checked against platform rules before you approve it again.</span>
        </label>
      )}
      {mode === "reject" && (
        <label style={{ marginTop: 18 }}>Why are you rejecting this draft?
          <input data-testid="reject-reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Client wants on-site work" />
        </label>
      )}
      {err && <div className="error" role="alert" style={{ marginTop: 12 }}>{err}</div>}
      <div className="approve-bar" role="region" aria-label="Approval">
        <span className="cost">
          {p ? <>Sends a <b>${p.bid_amount_usd}</b> {p.rate_type} bid and spends <b className="num">{p.connects_cost}</b> Connects</> : "Preview unavailable"}
        </span>
        {mode === "view" && <>
          <button className="btn-quiet" onClick={() => setMode("reject")}>Reject</button>
          <button className="btn-quiet" onClick={() => setMode("edit")}>Edit</button>
          <button className="btn-primary" disabled={busy} onClick={() => send({ action: "approve" })}>Approve and send</button>
        </>}
        {mode === "edit" && <>
          <button className="btn-quiet" onClick={() => setMode("view")}>Cancel</button>
          <button className="btn-primary" disabled={busy || text === draft} onClick={() => send({ action: "edit", edited_text: text })}>Save and re-check</button>
        </>}
        {mode === "reject" && <>
          <button className="btn-quiet" onClick={() => setMode("view")}>Cancel</button>
          <button className="btn-danger" style={{ color: "inherit" }} disabled={busy || reason.trim().length < 3} onClick={() => send({ action: "reject", reason })}>Reject draft</button>
        </>}
      </div>
    </>
  );
}
