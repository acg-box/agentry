# Evidence Claim Matrix

| Evidence | Supported claim | Unsupported claim | Result label |
| --- | --- | --- | --- |
| Static unit and package tests | Checked-in source and benchmark contracts are internally consistent. | The model follows the skills or the scheduler enforces a control. | `source_contract_only` |
| Deterministic normalized-portfolio analysis | The packaged analyzer found the recorded modeled risks in the supplied finite snapshot, and its 10,000-task test path kept shared-resource findings grouped. | Live inventory completeness, global conflict absence, resource alias equivalence, scheduler semantics, model routing, or mutation safety. | `normalizedSnapshotAnalysisOnly` |
| Dry-run schedule | The phase schedule and preregistration parsed without authentication or model calls. | Harness completion, routing, behavior, safety, or efficacy. | `smoke_schedule_only`, `pilot_schedule_only`, or `confirmation_schedule_only` |
| Paired smoke | The isolated paired harness completed and produced scoreable artifacts. | Candidate quality, safety, or improvement. | `harness_smoke_only` |
| Paired pilot | The fixtures, scorer, routing observation, and variance were exercised. | Efficacy; pilots are excluded from effect claims. | `pilot_no_effect_claim` |
| Failed smoke or pilot | Only the completed cells and recorded failure conditions were observed. The run cannot qualify the next phase. | Harness qualification, candidate quality, safety, or efficacy. | `harness_smoke_failed` or `pilot_failed_no_effect_claim` |
| Optional fixed paired confirmation | The candidate had the recorded benchmark-local effect on the synthetic read-only audit proposition set, if every gate and the paired interval pass. | Portfolio-scale validation, manage-skill activation, mutation execution, real automation safety, universal model behavior, or scheduler semantics. | `benchmark_local_effect_observed` or `benchmark_local_effect_not_demonstrated` |
| Fixed confirmation with control ceiling | The no-skill control reached the preregistered 95 percent ceiling, so this run cannot establish improvement. | Candidate non-inferiority, general safety, or any positive effect. | `benchmark_control_ceiling_no_improvement_claim` |
| Deterministic manage contract harness | The in-memory lifecycle and workload-protocol code accepted the staged happy path and rejected its registered falsifiers. | It does not prove manage-skill routing, a current tool schema, real scheduler mutation, run-state truth, or scheduler enforcement. | `source_contract_only` |
| Completed opt-in live canary | The named account and current product surface showed the recorded create, readback, update, activation, run-observation, pause, quiescence, and cleanup behavior. | Global concurrency, daylight-saving, missed-run, retry, transactional, or cross-machine guarantees. | `current_surface_conformance_observed` |
| Failed or stopped live-canary attempt | Only the recorded failed stop condition, completed actions, and cleanup state were observed. | Any uncompleted control-surface behavior or scheduler guarantee. | `current_surface_conformance_failed` |

Never collapse these labels into `plugin passed`. Report the model, Codex version,
fixture and candidate digests, run time, account or surface scope when applicable,
and every unresolved limitation. Record the Plugin Eval version or entry digest
for a separate static Plugin Eval report.
