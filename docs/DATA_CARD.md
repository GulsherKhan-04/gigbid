# Data card

| Field | Value |
|---|---|
| Sources | GigSim-lite (student-built, `simulator/generate.py`, seed 2026): 3 personas with 16-21 case studies, 6 repos, CV, 8 reviews and 150 proposals with outcomes each; 600 dev jobs with rule-based gold labels; 1,500 historical jobs. Replace with the instructor's GigSim persona corpora (CVs, case studies, repo READMEs and code, reviews, ~150 labelled past proposals per persona), historical jobs, dev set |
| Synthetic? | Yes (GigSim). No real client data is stored; live-mode data never enters the repo |
| Chunking | Paragraph-packed chunks of ~900 chars with 120 overlap; proposals and reviews kept whole |
| Metadata per chunk | persona, type, project, skills, date, client_industry, outcome |
| Index | Dense (nomic-embed-text via Ollama) + BM25, per persona, under `data/processed/` (git-ignored) |
| Known issues | Same project described several ways; implied skills; code vs prose mix |
| Hidden test set | Never in the repo |

Indexed chunks: ai-ml-engineer 187, data-analyst 190, fullstack-web-developer 192 (fastembed bge-small).
Known limitation: gold labels come from the same generator as the data, so they reward exact skill overlap.
