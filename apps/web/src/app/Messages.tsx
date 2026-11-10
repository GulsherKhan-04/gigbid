import { useCallback, useState } from "react";
import ApprovalPanel from "../components/ApprovalPanel";
import RunTimeline from "../components/RunTimeline";
import { Empty, ErrorBox, Loading } from "../components/States";
import { api } from "../lib/api/client";
import { useQuery } from "../lib/hooks";

type Thread = { thread_id: string; messages: { from: string; text: string }[]; status?: string; intent?: string };
type TState = { reply_draft?: { text: string; proposed_slots: string[] }; intent?: { intent: string }; pending_approval: unknown[]; status?: string };

export default function Messages() {
  const { data, error, loading, reload } = useQuery<Thread[]>("/api/messages");
  const [open, setOpen] = useState<string | null>(null);
  const thread = useQuery<TState>(open ? `/api/messages/${open}` : null, [open]);
  const refresh = useCallback(() => { void thread.reload(); void reload(); }, [thread, reload]);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} retry={reload} />;
  if (!data?.length) return <><div className="page-head"><h1>Messages</h1></div><Empty title="No client messages yet"><p>When a client replies to a proposal, the conversation appears here with a suggested reply.</p></Empty></>;
  const t = data.find((x) => x.thread_id === open);
  return (
    <>
      <div className="page-head"><div><h1>Messages</h1><p>Suggested replies wait for your approval before anything is sent.</p></div></div>
      <div className="grid-2">
        <div className="ledger">
          {data.map((x) => (
            <button key={x.thread_id} className="ledger-row" style={{ width: "100%", textAlign: "left", background: open === x.thread_id ? "var(--go-soft)" : "transparent", gridTemplateColumns: "1fr auto" }} onClick={() => setOpen(x.thread_id)}>
              <span><span className="title">{x.messages[x.messages.length - 1]?.text.slice(0, 80)}</span><span className="sub" style={{ display: "block" }}>{x.messages.length} messages</span></span>
              <span className={`badge ${x.intent === "scam_signal" ? "risk" : "neutral"}`}>{x.intent?.replace("_", " ") ?? "new"}</span>
            </button>
          ))}
        </div>
        {t && (
          <section className="panel">
            {t.messages.map((m, i) => <p key={i}><b>{m.from === "client" || !m.from ? "Client" : "You"}:</b> {m.text}</p>)}
            <hr style={{ border: 0, borderTop: "1px solid var(--line)" }} />
            {thread.data?.pending_approval.length ? (
              <>
                <h3>Suggested reply</h3>
                <div className="letter" style={{ padding: 20 }}>{thread.data.reply_draft?.text}</div>
                {!!thread.data.reply_draft?.proposed_slots.length && <p className="muted">Offers: {thread.data.reply_draft.proposed_slots.join("; ")}</p>}
                <ApprovalPanel endpoint={`/api/messages/${t.thread_id}/approval`} draft={thread.data.reply_draft?.text ?? ""} onDone={refresh} />
              </>
            ) : <button className="btn-primary" onClick={() => api(`/api/messages/${t.thread_id}/draft`, { method: "POST" })}>Suggest a reply</button>}
            <div style={{ marginTop: 16 }}><RunTimeline channel={`/api/messages/${t.thread_id}/stream`} onDone={refresh} /></div>
          </section>
        )}
      </div>
    </>
  );
}
