"""Portfolio ingestion: CVs (PDF), case studies (Markdown), repo READMEs and code, reviews and past proposals.

Every chunk carries metadata: persona, type, project, skills, date, client_industry, outcome (proposals).
The persona corpora from GigSim are expected under data/personas/<persona>/. The loader walks the folder
and classifies files by folder name and extension, so it tolerates small layout differences.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
CODE_EXT = {".py", ".ts", ".tsx", ".js", ".sql", ".ipynb", ".java", ".go", ".rs", ".r", ".scala"}


def _id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 2 <= size:
            cur = f"{cur}\n\n{p}" if cur else p
            continue
        if cur:
            chunks.append(cur)
        while len(p) > size:
            chunks.append(p[:size])
            p = p[size - overlap:]
        cur = p
    if cur:
        chunks.append(cur)
    return chunks


def _front_matter(text: str) -> tuple[dict[str, Any], str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    import yaml
    try:
        return yaml.safe_load(m.group(1)) or {}, text[m.end():]
    except Exception:
        return {}, text


def _skills_from(meta: dict, text: str) -> list[str]:
    s = meta.get("skills") or meta.get("tags") or []
    if isinstance(s, str):
        s = [x.strip() for x in s.split(",")]
    return [str(x) for x in s]


def _item(persona: str, kind: str, project: str, text: str, meta: dict, source: str) -> dict:
    return {
        "persona": persona, "type": kind, "project": project, "text": text, "source": source,
        "skills": _skills_from(meta, text), "date": str(meta.get("date", "")),
        "client_industry": meta.get("client_industry") or meta.get("industry", ""),
        "outcome": meta.get("outcome", ""), "title": meta.get("title", project),
        "evidence_id": meta.get("evidence_id") or meta.get("id"),
    }


def load_persona_dir(persona_dir: Path) -> Iterable[dict]:
    persona = persona_dir.name
    for f in sorted(persona_dir.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else str(f)
        low = str(f).lower()
        if f.suffix == ".pdf":
            from pypdf import PdfReader
            text = "\n\n".join(p.extract_text() or "" for p in PdfReader(str(f)).pages)
            yield _item(persona, "cv", "cv", text, {}, rel)
        elif f.suffix in {".json", ".jsonl"} and ("proposal" in low or "review" in low):
            rows = ([json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
                    if f.suffix == ".jsonl" else json.loads(f.read_text(encoding="utf-8")))
            for i, r in enumerate(rows if isinstance(rows, list) else [rows]):
                kind = "proposal" if "proposal" in low else "review"
                text = r.get("text") or r.get("cover_letter") or r.get("body") or r.get("review") or json.dumps(r)
                yield _item(persona, kind, r.get("project", r.get("job_title", f"{kind}-{i}")), text, r,
                            f"{rel}#{r.get('id', i)}")
        elif f.suffix == ".md":
            meta, body = _front_matter(f.read_text(encoding="utf-8", errors="ignore"))
            kind = ("readme" if f.name.lower() == "readme.md" else
                    "proposal" if "proposal" in low else "review" if "review" in low else
                    "cv" if "cv" in f.stem.lower() or "resume" in f.stem.lower() else "case_study")
            project = f.parent.name if kind == "readme" else f.stem
            yield _item(persona, kind, project, body, {**meta, "title": meta.get("title", project)}, rel)
        elif f.suffix in CODE_EXT:
            text = f.read_text(encoding="utf-8", errors="ignore")[:6000]
            project = next((p for p in f.relative_to(persona_dir).parts[:-1] if p not in {"repos", "src", "code"}),
                           f.parent.name)
            yield _item(persona, "code", project, f"# {f.name}\n{text}", {}, rel)


def load_sample(path: Path) -> Iterable[dict]:
    for r in json.loads(path.read_text(encoding="utf-8")):
        yield {"persona": r.get("freelancer_id", "sample"), "type": r.get("type", "case_study"),
               "project": r.get("title", r["evidence_id"]), "title": r.get("title", ""),
               "text": f"{r.get('title', '')}\n\n{r.get('summary', '')}", "skills": r.get("skills", []),
               "date": r.get("date", ""), "client_industry": r.get("client_industry", ""),
               "outcome": r.get("outcome", ""), "source": f"{path.name}#{r['evidence_id']}",
               "evidence_id": r["evidence_id"]}


def build_chunks(items: Iterable[dict]) -> list[dict]:
    out = []
    for it in items:
        parts = chunk_text(it["text"]) if it["type"] not in {"proposal", "review"} else [it["text"]]
        for n, c in enumerate(parts):
            out.append({**it, "text": c, "chunk": n,
                        "evidence_id": (it["evidence_id"] if len(parts) == 1 else f"{it['evidence_id']}#{n}")
                        if it.get("evidence_id") else _id(it["source"], str(n))})
    return out


def load_all(persona: str | None = None) -> list[dict]:
    items: list[dict] = []
    pdir = ROOT / "data" / "personas"
    if pdir.exists():
        for d in sorted(p for p in pdir.iterdir() if p.is_dir()):
            if persona in (None, d.name):
                items.extend(load_persona_dir(d))
    sample = ROOT / "data" / "sample" / "portfolio_items.json"
    if not items and sample.exists():
        items.extend(load_sample(sample))
    return build_chunks(items)
