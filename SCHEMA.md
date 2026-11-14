# Relational model

Every table's first field is its immutable primary key. IDs use zero-padded counters. Monthly demand uses DEM-PRJ-2026-NNNNNN-2026MNN, a monthly equivalent of the brief's illustrative weekly convention. The intentionally duplicated demand uses an explicit exception ID.

* Role 1:N Employee and 1:N DemandPlan; both references required.
* Employee N:M Skill through EmployeeSkill; employee/skill pair unique. Both references required.
* Project 1:N DemandPlan; Skill 1:N DemandPlan. All required.
* Employee N:M DemandPlan through Allocation; both references required; repeated allocations are possible and retain distinct IDs.
* Employee 1:N Availability; employee/month pair unique; every employee has each planning month.
* Employee N:M Skill through Training; planned development with required employee and skill references.
* DemandPlan 1:0..1 GapAnalysis; duplicate demand excluded from canonical analysis has no gap row.
* Employee 1:N GapAnalysis through optional candidate_id; empty means no training candidate. Candidate actions do not create employees or promises of availability.
* Entity record 1:N Event through entity/record_id, validated polymorphically. Creation events retained for Employee, Project, DemandPlan and Training.

Employee effective_from defines baseline active date; Project start/end bounds the planning year. Availability and DemandPlan are monthly effective snapshots; Allocation days are inclusive within its demand month. EmployeeSkill last_verified controls 365-day validity. Training has start/end and lifecycle status. No deletes or in-place history updates are performed.

Business exceptions are findings, not structural FK corruption. ground_truth is a separate evaluation artifact keyed by entity/record_id/issue_type. Validation rejects duplicate primary keys, broken foreign keys, invalid ranges/enums, date ordering, unsupported creation events, and reconciliation failures. Natural demand-key duplicates are retained and flagged. All rows derive from lawful synthetic generation.
