# Data card

Every row carries a `source` field: `real:...` or `synthetic`. Results must say which data they come from.

## Real data
| Field | Value |
|---|---|
| Dataset | Upwork Job Postings Dataset 2024 (50k records), by asaniczka on Kaggle: kaggle.com/datasets/asaniczka/upwork-job-postings-dataset-2024-50k-records |
| Recommended by | Course TA (Classroom post), as a source of real job data |
| Licence | TODO: copy the licence shown on the Kaggle page and keep a screenshot in docs/images/ |
| Raw file | `data/raw/upwork-jobs.csv` (53,058 rows, 72 MB; git-ignored, download from Kaggle) |
| Columns used | title, link (de-duplication only), description, published_date, is_hourly, hourly_low, hourly_high, budget, country |
| Preprocessing (`simulator/real_data.py`) | drop rows without title, description (< 80 chars) or price; de-duplicate by link and by title + description start; collapse whitespace; truncate descriptions to 1,500 chars; parse fixed budget or hourly range; match each job to the persona whose skills it names most (word-boundary match) or `other`; extracted skills become `required_skills` |
| After cleaning | 42,950 jobs (20,981 fixed, 21,969 hourly); persona matches: data analyst 2,890, full-stack 2,183, AI/ML 1,476, other 36,401 |
| Used for | job stream and dev-set postings (`data/real/jobs_used.jsonl`, about 550 rows); pricing statistics from all 20,981 fixed budgets (`data/historical_jobs.json`) |
| Personal data | none beyond country; links are not shown in the app |

## Synthetic data (`simulator/generate.py`, seed 2026)
| What | Why synthetic |
|---|---|
| 3 freelancer personas: CV, 16-21 case studies, 6 repos, 8 reviews, 150 past proposals with outcomes each | no public dataset has portfolios linked to proposals and outcomes |
| 300 clients with history and hidden preferences | the job dataset has no client identities or histories |
| Scam, free-work and off-platform posts (about 18% of the dev set) | the dataset has no scam labels |
| Prompt-injection sentences planted into some real posts (`source` ends with `+synthetic-injection`) | needed to test the injection defence |
| Client replies and conversations (simulated clients in `simulator/server.py`) | no real client behaviour data |

## Gold labels (dev set, 200 jobs per persona)
Rule-based and reproducible (`label_job` in `simulator/generate.py`): scam, free work or off-platform means skip;
two or more required skills proven by portfolio projects means bid; exactly one means watch; none means skip;
bids below the persona's floor (fixed) or 60% of its hourly rate (hourly) mean skip. Evidence = projects (case study
and repo) proving a required skill. Fair price band = posted budget +/- 20% (fixed) or the posted hourly range.

## Limitations
- Gold labels are written by the same author as the system, and reward exact skill-name overlap; skills implied
  but not named in a post are missed.
- Required skills come from keyword matching, so a post saying "ML model" without naming a library has none.
- Fixed-price "fair band" is the posted budget, not the final agreed price (the dataset has no outcomes).
- Persona corpora are synthetic, so retrieval difficulty is controlled by the generator.
- Reply and hire rates come from simulated clients, not real ones.
