import { Fragment, useState } from "react";

export type Claim = { text: string; status: string; evidence_ids: string[] };
export type Evidence = Record<string, { evidence_id: string; title?: string; project?: string; type: string; source: string; text: string; outcome?: string }>;

/** Renders the proposal as a letter. Each verified claim is highlighted; hover or focus shows its evidence. */
export default function EvidenceLetter({ text, claims, evidence }: { text: string; claims: Claim[]; evidence: Evidence }) {
  const [open, setOpen] = useState<number | null>(null);
  const clean = text.replace(/\s*\[[0-9a-z-]{6,}\]/gi, "");
  const spans: { start: number; end: number; i: number }[] = [];
  claims.forEach((c, i) => {
    const needle = c.text.replace(/\s*\[[0-9a-z-]{6,}\]/gi, "").trim();
    const at = needle ? clean.indexOf(needle) : -1;
    if (at >= 0 && !spans.some((s) => at < s.end && at + needle.length > s.start)) spans.push({ start: at, end: at + needle.length, i });
  });
  spans.sort((a, b) => a.start - b.start);
  const parts: (string | { i: number; t: string })[] = [];
  let pos = 0;
  for (const s of spans) { parts.push(clean.slice(pos, s.start), { i: s.i, t: clean.slice(s.start, s.end) }); pos = s.end; }
  parts.push(clean.slice(pos));

  return (
    <div className="letter" data-testid="letter">
      {parts.map((p, k) => typeof p === "string" ? (
        <Fragment key={k}>{p.split(/\n\n+/).map((para, j, arr) => <Fragment key={j}>{para}{j < arr.length - 1 && <><br /><br /></>}</Fragment>)}</Fragment>
      ) : (
        <mark key={k} className={`claim ${claims[p.i].status === "partly_supported" ? "partly" : ""}`} tabIndex={0}
          onMouseEnter={() => setOpen(p.i)} onMouseLeave={() => setOpen(null)} onFocus={() => setOpen(p.i)} onBlur={() => setOpen(null)}
          aria-describedby={open === p.i ? `ev-${p.i}` : undefined}>
          {p.t}<span className="cite">{claims[p.i].evidence_ids.length}</span>
          {open === p.i && (
            <span className="hover-card" role="tooltip" id={`ev-${p.i}`}>
              {claims[p.i].evidence_ids.map((id) => evidence[id] ? (
                <span key={id} style={{ display: "block", marginBottom: 8 }}>
                  <strong>{evidence[id].title || evidence[id].project}</strong>
                  {evidence[id].type.replace("_", " ")}{evidence[id].outcome ? `, ${evidence[id].outcome}` : ""}
                  <span style={{ display: "block", marginTop: 4 }}>{evidence[id].text.slice(0, 220)}…</span>
                </span>
              ) : <span key={id}>Evidence {id}</span>)}
              {claims[p.i].status === "partly_supported" && <em>Only partly supported by this evidence.</em>}
            </span>
          )}
        </mark>
      ))}
    </div>
  );
}
