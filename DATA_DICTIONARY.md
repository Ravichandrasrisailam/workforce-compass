# Data dictionary

All fields below are required unless marked optional. IDs are immutable strings, unique only when designated PK. Foreign keys must exist in the named parent. Text is UTF-8, dates ISO YYYY-MM-DD, periods YYYY-MM. Hours are integer planning hours, never negative. No employee data is real. This dictionary describes generation and validation contracts; some domain invariants follow directly from construction rather than separate validator checks.

## Employee
* employee_id: string PK; EMP-NNNNNN; unique, nonempty.
* name: string; synthetic display name; nonempty; not a unique key.
* role_id: string FK Role; one primary role per employee.
* weekly_hours: integer hours/week; 20, 32 or 40; part-time capacity basis.
* status: string enum active; current baseline lifecycle.
* effective_from: date; 2026-01-01; no baseline availability precedes this.

## Role
* role_id: string PK; ROL-NNNNNN; unique.
* name: string; Engineer, Analyst, Designer or Project Manager; unique in generated taxonomy.

## Skill
* skill_id: string PK; SKL-NNNNNN; unique.
* name: string; Specialty NNN; unique generated label.
* category: string enum Engineering, Analytics, Design, Delivery.
* validity_days: integer days; 365; shared verification policy.

## EmployeeSkill
* employee_skill_id: string PK; ES-NNNNNNN; unique.
* employee_id: string FK Employee; required.
* skill_id: string FK Skill; employee/skill combination unique.
* proficiency: integer ordinal 1..5; beginner, basic, competent, advanced, expert.
* last_verified: date; must precede planning start in baseline; expiry derived by adding 365 days.
* treated_current: integer boolean 0 or 1; source claim only; never overrides expiry. Injected stale-current exception is labelled separately.

## Project
* project_id: string PK; PRJ-2026-NNNNNN; unique.
* name: string; Initiative NNNN; nonempty.
* status: string enum active.
* start_date: date; 2026-01-01; <= end_date.
* end_date: date; 2026-12-31.

## DemandPlan
* demand_id: string PK; DEM-{project_id}-2026MNN; unique. Exception row DEM-DUPLICATE-2026M01 preserves its own PK.
* project_id: string FK Project.
* period: string YYYY-MM; month 01..12 in 2026; inside project dates.
* role_id: string FK Role.
* skill_id: string FK Skill.
* min_proficiency: integer ordinal 2..4.
* required_hours: integer hours/month; 80, 160, 240 or 320.
* status: string enum approved.
* Natural key: project_id/period/role_id/skill_id; duplicates flagged and excluded from canonical demand totals.

## Allocation
* allocation_id: string PK; ALLOC-2026-NNNNNN; unique.
* employee_id: string FK Employee.
* demand_id: string FK DemandPlan; establishes project and period.
* hours: integer assigned hours/month; baseline 40, 80 or 120; injected overload 400; >= 0.
* start_day: integer inclusive day in demand month; 1..31, baseline 1.
* end_day: integer inclusive day; >= start_day, baseline 28; all generated intervals valid in every 2026 month.

## Availability
* availability_id: string PK; AV-NNNNNNNN; unique.
* employee_id: string FK Employee.
* period: string YYYY-MM; employee/period pair unique.
* base_hours: integer hours; Employee.weekly_hours × 4.
* leave_hours: integer hours; 0, 8, 16 or 32; <= base_hours.
* available_hours: integer hours; base_hours − leave_hours; positive in generated data.

## Training
* training_id: string PK; TRN-NNNNNN; unique.
* employee_id: string FK Employee.
* skill_id: string FK Skill; intended skill development.
* status: string enum planned, in_progress, completed, cancelled; generated planned.
* start_date: date; 2026-02-01; <= end_date.
* end_date: date; 2026-03-01.
* target_proficiency: integer ordinal 1..5; generated 4; no immediate change to profile.

## GapAnalysis
* gap_id: string PK; GAP-NNNNNNN; unique.
* demand_id: string FK DemandPlan; unique among canonical demand rows.
* required_hours: integer hours; equals referenced demand requirement.
* allocated_hours: integer hours; sum of source allocations for demand.
* qualified_hours: integer hours; sum of role/skill/proficiency/current-verification-qualified allocation hours capped at required_hours.
* gap_hours: integer hours; required_hours − qualified_hours; >= 0.
* recommendation: string enum none, train, hire; derived from gap and eligible candidates.
* candidate_id: optional string FK Employee; empty when no training candidate; populated only for train.
* assumption: string; recommendation constraints and manager review caveat; nonempty.

## Event
* event_id: string PK; EVT-NNNNNNNN; unique.
* entity: string enum Employee, Project, DemandPlan, Training.
* record_id: string polymorphic FK to entity PK.
* from_state: string; none for initial creation.
* to_state: string; referenced row's initial status.
* effective_date: date; 2026-01-01 baseline record creation date; distinct from scheduled training dates.
* event_type: string enum created; immutable historical record.

## Derived/evaluation exports
* utilization: employee_id/period composite key; available_hours and allocated_hours integers; utilization_pct decimal percent rounded to two places; risk enum overallocated, underutilized, balanced.
* findings and ground_truth: entity/record_id/issue_type composite key; issue_type enum allocation_exceeds_availability, overlapping_projects, stale_skill_treated_current, demand_double_counted. Findings are rule outputs. Ground truth independently records deliberate injections at generation time and never becomes an input feature.
* manifest.json: config, provenance and per-file SHA-256 hex digests.
* validation_summary.json: integrity errors, boolean passed, known_anomaly_recall 0..1, row counts, exception counts, reconciled canonical demand and gap totals.
