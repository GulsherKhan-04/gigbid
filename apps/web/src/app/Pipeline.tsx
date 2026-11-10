import { Link } from "react-router-dom";
import { ErrorBox, Loading } from "../components/States";
import { api, type JobRow } from "../lib/api/client";
import { useQuery } from "../lib/hooks";

const LANES = [["drafted", "Drafted"], ["submitted", "Submitted"], ["viewed", "Viewed"], ["replied", "Replied"],
  ["interview", "Interview"], ["hired", "Hired"], ["lost", "Lost"]] as const;
const NEXT: Record<string, string[]> = { submitted: ["viewed", "replied", "lost"], viewed: ["replied", "lost"],
  replied: ["interview", "lost"], interview: ["hired", "lost"] };

export default function Pipeline() {
  const { data, error, loading, reload } = useQuery<JobRow[]>("/api/jobs");
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} retry={reload} />;
  const move = async (id: string, outcome: string) => { await api(`/api/jobs/${id}/outcome`, { method: "POST", json: { outcome } }); reload(); };
  return (
    <>
      <div className="page-head"><div><h1>Pipeline</h1><p>Every proposal from draft to hire. Outcomes teach GigBid what works.</p></div></div>
      <div className="board">
        {LANES.map(([key, label]) => {
          const cards = (data ?? []).filter((r) => r.stage === key);
          return (
            <section className="lane" key={key} aria-label={label}>
              <h3>{label}<span className="muted num">{cards.length}</span></h3>
              {cards.map((c) => (
                <div className="ticket" key={c.job_id}>
                  <Link to={key === "drafted" ? `/studio/${c.job_id}` : `/jobs/${c.job_id}`}>{c.title}</Link>
                  <div className="muted num">{c.price ? `$${Math.round(c.price)}` : ""}</div>
                  {NEXT[key] && <div className="row" style={{ marginTop: 6, gap: 6 }}>
                    {NEXT[key].map((n) => <button key={n} className="chip" onClick={() => move(c.job_id, n)}>Mark {n}</button>)}
                  </div>}
                </div>
              ))}
            </section>
          );
        })}
      </div>
    </>
  );
}
