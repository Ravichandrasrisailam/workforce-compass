# Workforce Compass

A local web application for workforce capacity and skills planning, built with Python's standard library and plain HTML/CSS/JavaScript. It forecasts planned demand by project, role, skill and month; identifies qualified coverage, skill gaps, capacity risks and hiring/training options; and preserves source records and creation events for audit.

## Start the UI

```sh
python app.py --open
```

Open **http://127.0.0.1:8000**. On Windows, you can also double-click `start.bat`. No npm install, pip install, API keys, or internet connection is needed. The application creates its dataset in memory, so there is no prerequisite generator command. Keep the terminal running; press Ctrl+C there to stop. If port 8000 is in use, run `python app.py --port 8001 --open`.

### What are we trying to achieve?

Help a company answer: **Can we deliver upcoming projects with our current people, skills and available time? If not, where do we need to reassign, train or hire?** Headcount alone misses part-time schedules, leave, outdated skill evidence and double-booked people. This app brings those factors together and explains each decision.

### Explore the application

1. **Understand the project** explains the problem, actors, workflow, formulas, a worked example and the submission requirements.
2. **Overview** shows demand, qualified coverage, gaps, capacity, a 12-month trend, role gaps and next actions. Click a month in the chart or change the filters.
3. **Demand & skill gaps** supports searching and recommendation filters. Select **Explore** to inspect the source demand, employee assignments, skill evidence, qualification failures and creation events.
4. In a demand trace, use **What if?** to change required hours or simulate skill reverification. Results are recalculated by the same engine in isolation; the baseline stays unchanged. This simulates a completed verification, not an automatic approval of a real employee's skills.
5. **People & capacity** shows leave-adjusted capacity, assignments and utilization. Open **Profile** to inspect skills and project assignments. Search supports all employee IDs; the list displays the first 100 matching people sorted by utilization.
6. **Exceptions** explains all four required negative scenarios and distinguishes known injected cases from naturally occurring findings. It displays the first 200 matching findings; export retrieves all.
7. Switch **Dataset** to **Full scale** for 5,000 employees, 300 skills, 500 projects and 12 months. Initial calculation may take a few seconds.

Month/project/role filters scope demand and gaps. Capacity covers all assignments of the employees in scope, including other projects. Exception counts cover the whole selected dataset. CSV exports contain the whole selected dataset, independent of filters. These scopes are labelled in the UI. The local service binds only to 127.0.0.1 and has no account or deployment requirement.

The starter January scenario has 2,000 demand hours, 1,320 provisionally qualified hours and a 680-hour gap with the default seed. Suitable and unsuitable assignments are both generated, so users can explore covered work, training candidates, hiring reviews and capacity exceptions. The dataset is illustrative, not a claim about a real organization.

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

Train recommendations require a current profile one proficiency level below the requirement, matching role, and at least min(gap,40) free hours. Other unmet demand recommends hiring subject to budget approval. These are candidate actions, not automatic hiring decisions or claims that one employee can close an entire gap. Planned training does not immediately increase proficiency. The taxonomy uses familiar role/skill names such as Engineer, Python and SQL; full mode adds numbered synthetic skill specializations. All profiles and project demand remain synthetic.

## Exceptions and evaluation

Four deliberately labelled cases: an allocation of 400 hours, overlapping projects, a stale profile claimed current, and duplicate demand with a separate immutable ID. Inputs retain every source row. Duplicate natural demand keys (project/month/role/skill) are excluded from gap totals but reported as exceptions. Other allocation and overlap risks can arise naturally; findings include these too. Known-anomaly recall measures recovery of injected labels only. Precision is deliberately not reported because naturally occurring exceptions are not exhaustively labelled. Tests cover integrity failures, arithmetic, expiry, exceptions, seed variation and byte-identical exports.

`Event` is an append-only creation journal. No operational updates are implemented; future transitions must append events rather than replace prior event records. Training states are planned/in_progress/completed/cancelled; supplied data starts planned. Events in this version record only none → initial state. No external systems, authentication, live HR imports, optimization or predictive-model accuracy is claimed.

## Data and architecture

`workforce.py`: master generation → dependent records → isolated labelled injections → deterministic analysis → validation → CSV/JSON/SQLite seed export → SHA-256 manifest. Staffing selects up to two role/skill/proficiency/current-verification-matched employees, then fills remaining assignments from other employees to exercise mismatch cases. Master profiles and demand vary with the fixed seed. `app.py` exposes the engine through a loopback HTTP service; `web/` contains the responsive UI. `test_workforce.py` and `test_app.py` test engine behavior, filtering, trace reconciliation, scenario isolation, HTTP endpoints and exports; `verify_reproducibility.py` runs the full pipeline twice and compares every export checksum and row count. See [SCHEMA.md](SCHEMA.md) and [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

All names and records are synthetic. No personal data, public dataset, external license, or redistributable third-party asset is used. The manifest records provenance, generator parameters, row counts through validation_summary, and file checksums. SQL exports are portable SQLite seed snapshots; relational validation occurs in Python before export. The seed tables intentionally preserve labelled business anomalies.

## Public GitHub submission

Repository: https://github.com/Ravichandrasrisailam/workforce-compass

Submit this public repository URL. Clone it and run the commands above to reproduce the project and verification outputs.
