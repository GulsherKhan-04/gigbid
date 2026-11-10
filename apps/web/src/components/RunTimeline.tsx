import { useEffect, useState } from "react";
import { stream, type RunEvent } from "../lib/api/client";

const LABEL: Record<string, string> = {
  scout: "Loaded the job", analyst: "Read the brief", risk_assessor: "Checked for risks", fit_matcher: "Matched your portfolio",
  decision: "Decided bid or skip", pricing: "Priced the bid", writer: "Drafted the proposal", verifier: "Checked every claim",
  critic: "Reviewed the draft", compliance: "Checked platform rules", approval: "Recorded your decision", submit: "Sent to the marketplace",
  client_liaison: "Drafted a reply", send: "Sent the reply", not_worth: "Connects not worth it", needs_attention: "Stopped: budget exceeded",
};

/** Live node-by-node progress streamed from LangGraph over SSE. */
export default function RunTimeline({ channel, onDone, initial = [] }: { channel: string; onDone?: () => void; initial?: RunEvent[] }) {
  const [events, setEvents] = useState<RunEvent[]>(initial);
  const [live, setLive] = useState(false);
  useEffect(() => stream(channel, (e) => {
    if (e.type === "run_started") { setLive(true); setEvents([]); }
    if (e.type === "node" || e.type === "error") setEvents((x) => [...x, e]);
    if (e.type === "run_finished" || e.type === "interrupt") { setLive(false); onDone?.(); }
  }), [channel, onDone]);
  if (!events.length && !live) return <p className="muted">No run in progress right now.</p>;
  return (
    <ol className="timeline" aria-live="polite">
      {events.map((e, i) => (
        <li key={i}>
          <span className={`dot ${e.type === "error" ? "err" : ""}`} />
          <span><b>{e.node ? LABEL[e.node] ?? e.node : "Error"}</b>{e.error && <span className="muted"> {e.error}</span>}
            {e.trace?.model && <span className="muted"> · {e.trace.model}</span>}</span>
          <span className="muted num">{e.elapsed?.toFixed(1)}s</span>
        </li>
      ))}
      {live && <li><span className="dot live" /><span>Working…</span><span /></li>}
    </ol>
  );
}
