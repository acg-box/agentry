# Opt-In Scheduled Conformance Canary

This canary changes real Scheduled tasks. Do not start it from a request to
design, audit, review, or test synthetic fixtures. Obtain explicit authority for
the exact canary prefix and for create, activate, update, pause, and delete.

## Stop Conditions

Stop before creation when any condition is false:

- The current supported tool can create a paused task, return a stable ID, view
  the full definition, update the full definition, and read it back.
- Supported evidence can show active-run state or quiescence.
- The target is a dedicated disposable project.
- The exact task prefix, maximum task count, maximum duration, and cleanup owner
  are recorded.
- The task has no connector, secret, network access, production data, external
  side effect, or notification to another person.
- The workload writes only harmless append-only receipts under the disposable
  project.

Do not inspect or edit private scheduler files or databases. If a stop condition
appears after creation, pause the exact canary tasks and report their stable IDs.
Do not delete a task when quiescence is unknown.

## Conformance Sequence

1. Discover the current tool and record its live schema and supported surfaces.
2. Create one exact canary in the paused state. Read back every field.
3. Change one harmless field with a full update. Verify that all other fields are
   unchanged through readback.
4. Activate one harmless run. Record start, end, result, and receipt evidence when
   the supported surface exposes them.
5. Pause the canary. Do not infer that pause terminated an active run.
6. Establish quiescence from supported run evidence.
7. Delete only the explicitly authorized stable ID. Verify the result.

Optional extensions require separate exact authority:

- Two resource-disjoint tasks can record observed start and end times. One run can
  show observed overlap or serialization, but it cannot establish a scheduler
  guarantee.
- A guarded consumer can first fail closed on a missing synthetic receipt, then
  succeed after a producer publishes a matching cycle and version.
- A disposable local database can exercise idempotent replay and target-enforced
  fencing. This tests the workload protocol, not a Codex scheduler feature.
- A barrier-controlled task can show that pause does not terminate the current
  run, when the product exposes enough run evidence.

Do not use a short canary to claim daylight-saving, missed-run, downtime catch-up,
retry, cross-machine fencing, or transactional publication behavior. Use a
controlled-clock workload test for guards, and leave undocumented scheduler
semantics unknown.

## Receipt

Record the exact authorized prefix, stable IDs, account and project scope, tool
schema observation time, prior and final definitions, readback comparisons, run
evidence, cleanup result, and every task left paused. Use result label
`current_surface_conformance_observed` only when all requested steps complete.
Otherwise use `current_surface_conformance_failed` and state the stop condition.
