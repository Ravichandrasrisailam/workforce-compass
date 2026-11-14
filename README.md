# Workforce Compass

A reproducible workforce capacity and skills planning project, built with Python's standard library. It forecasts planned demand by project, role, skill and month; identifies qualified coverage, skill gaps, capacity risks and hiring/training options; and preserves source records and creation events for audit.

## Run

Requires Python 3.10+; no packages, API keys or external data required.

```sh
python workforce.py
python workforce.py --full --output output-full
python -m unittest -v
python verify_reproducibility.py
```

The starter dataset contains 100 employees, 30 skills, 10 projects and 12 months. Full mode contains 5,000 employees, 300 skills, 500 projects and 12 months. Override counts with `--employees`, `--skills`, `--projects`, `--months` and `--seed`. Default seed: 20261022. Outputs are local and ignored by Git; regenerate them from the committed code.

## Submission demo

1. Run the starter command and tests.
2. Open `output/validation_summary.json`: check integrity, demand/gap totals, exception counts and known-anomaly recall.
3. Inspect `output/GapAnalysis.csv`: follow demand_id into DemandPlan, then role/skill/project master records. Inspect utilization.csv for leave-adjusted risk.
4. Compare findings.csv with the separately exported ground_truth.csv. Ground truth is passed only to evaluation/export, never to analyze().
5. For the required scale, run full mode and the reproducibility script. Committed verification results record the measured full-scale run.
6. Load SQL with `sqlite3 workforce.db < output-full/seed.sql` if the optional sqlite3 CLI is installed. CSV and JSON need no extra tools.

## Decisions and assumptions

Demand is a deterministic **scenario forecast supplied through approved demand plans**, not a learned statistical forecast. A 2026 planning year has 12 fixed four-week capacity buckets: weekly hours × 4 minus leave hours. This intentionally uses 48 planning weeks, not calendar working-day accounting. Proficiency is 1 (beginner) to 5 (expert). Verification expires after 365 days, evaluated at the demand month's first day; a claimed current flag never overrides expiry.

Only allocations with the required role, skill, proficiency and valid verification contribute qualified coverage; coverage is capped at required hours. Gap = demand − qualified coverage. Allocation totals preserve oversupply. Utilization = allocated / available hours, including part-time and leave. Above 100% is overallocated, below 60% is underutilized. Capacity exceptions require manager review: qualified coverage is provisional when concurrent assignments exist and does not constitute a feasible scheduling optimizer.

Train recommendations require a current profile one proficiency level below the requirement, matching role, and at least min(gap,40) free hours. Other unmet demand recommends hiring subject to budget approval. These are candidate actions, not automatic hiring decisions or claims that one employee can close an entire gap. Planned training does not immediately increase proficiency. Role/skill IDs are generic synthetic taxonomy labels.

## Exceptions and evaluation

Four deliberately labelled cases: an allocation of 400 hours, overlapping projects, a stale profile claimed current, and duplicate demand with a separate immutable ID. Inputs retain every source row. Duplicate natural demand keys (project/month/role/skill) are excluded from gap totals but reported as exceptions. Other allocation and overlap risks can arise naturally; findings include these too. Known-anomaly recall measures recovery of injected labels only. Precision is deliberately not reported because naturally occurring exceptions are not exhaustively labelled. Tests cover integrity failures, arithmetic, expiry, exceptions, seed variation and byte-identical exports.

`Event` is an append-only creation journal. No operational updates are implemented; future transitions must append events rather than replace prior event records. Training states are planned/in_progress/completed/cancelled; supplied data starts planned. Events in this version record only none → initial state. No external systems, authentication, live HR imports, optimization or predictive-model accuracy is claimed.

## Data and architecture

`workforce.py`: master generation → dependent records → isolated labelled injections → deterministic analysis → validation → CSV/JSON/SQLite seed export → SHA-256 manifest. `test_workforce.py` tests behavior; `verify_reproducibility.py` runs the full pipeline twice and compares every export checksum and row count. See [SCHEMA.md](SCHEMA.md) and [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

All names and records are synthetic. No personal data, public dataset, external license, or redistributable third-party asset is used. The manifest records provenance, generator parameters, row counts through validation_summary, and file checksums. SQL exports are portable SQLite seed snapshots; relational validation occurs in Python before export. The seed tables intentionally preserve labelled business anomalies.

## Public GitHub submission

Repository: https://github.com/Ravichandrasrisailam/workforce-compass

Submit this public repository URL. Clone it and run the commands above to reproduce the project and verification outputs.
