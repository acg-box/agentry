---
name: manage
description: Design or change Codex Scheduled tasks or recurring automations with explicit mutation authority. Use when the user's request or inspected evidence positively identifies a Codex Scheduled definition, recurring cadence, thread follow-up, monitor, reminder, or stable task ID and the user requests create, update, pause, activate, coordinate, or retire. For a generic review of named files, inspect those files before choosing this skill. Do not trigger it from a safety prohibition, rejected proposal, label, denial, or out-of-scope mention alone.
---

# Manage Automations

A request to design, explain, review, or audit does not authorize a mutation.
Create, update, pause, resume, or delete only when the user explicitly requests
that action. Keep audit work read-only and route it to `$automation:audit`.
Authority to change an automation does not authorize repository, connector,
credential, claim, worktree, or external-workload changes. Require separate
explicit authority and exact targets for those actions. Otherwise report them as
pending work.

Load detail only for the action in scope:

- Read `../../references/authority-and-lifecycle.md` only when capability
  evidence, staged activation, quiescence, incompatible change, or retirement
  evidence needs evaluation.
- Read `../../references/contract-and-coordination.md` only when the design has
  a dependency, shared writer, overlap, backlog, replay, mixed-scheduler, receipt,
  claim, lease, or fencing risk.

Do not load both references by default.

## Discover the Supported Surface

1. Find the current supported automation-management tool before you act. Use its
   live schema and instructions. Do not invent task fields, edit private scheduler
   files or databases, emit raw automation directives, or show raw RRULE strings
   to the user.
2. Resolve existing tasks by name, prompt, target, and stable ID. View the resolved
   task before a change. Prefer an update over a duplicate and preserve every
   unchanged field in the full update payload.
3. State which task types and schedulers the current tool can control. Treat web,
   event, monitor, one-shot, or external-scheduler tasks as out of scope when the
   current tool cannot read or change them.

Follow the live tool's defaults for same-chat follow-ups versus standalone work,
notifications, and supported scheduling. Do not copy a fixed tool schema into the
prompt or create a different task type to bypass an unsupported operation.

## Design the Coordination Contract

When coordination risk exists, use the coordination reference to complete the
core record and select the smallest sufficient workload contract. Independent,
resource-disjoint tasks need no dependency or writer protocol.

For a guarded dependency, require a stable cycle identity and a success receipt
whose consumer verifies cycle, version, and freshness and fails closed. For a
shared writer, require idempotency and a target-enforced claim or lease with
fencing. Receipt publication, claims, leases, fencing, and stale-writer rejection
are required workload contracts; route their implementation and enforcement to
the workload or platform owner under separate authority. This plugin only records
the requirement and coordinates the automation definition.

When the required workload contract is unavailable, prevent concurrent
activation, coalesce the work, or use an external orchestrator. Do not claim that
this plugin supplies the guarantee.

## Create and Activate

For a simple reminder or independent read-only follow-up with no dependency,
shared writer, overlap, or replay risk, resolve an existing definition, use the
supported tool to create or update the requested task, and read back its state.
Follow the tool's activation defaults and the user's notification intent. Do not
require a paused trial, workload execution, or a portfolio audit for this path.
A definition readback proves scheduling configuration, not a future run's result.

Use the staged path below when workload effects or coordination risk require it:

1. Audit the known scope and check for an existing task before creation.
2. Validate the prompt with a safe preview or applicable existing evidence matched
   to the intended prompt, model, tools, permissions, target, and execution
   environment. Run the underlying workload only within authority for its actual
   effects; permission to create a schedule does not authorize an immediate run.
   A preview does not prove execution. Report untested behavior and keep any
   risk-dependent activation gate open until its required evidence is available.
   This need not block authorized paused definition creation when the supported
   surface permits it.
3. Review time-zone meaning, downtime and catch-up behavior, runtime envelope,
   partial failure, replay, overlap, notifications, and retirement criteria.
4. Create the task paused when the supported surface permits it. Otherwise state
   the activation risk before creation.
5. Read back the created definition. Activate one new dependency edge or
   shared-writer change at a time, then review the first runs and their side
   effects.

## Change

Scope the procedure to what the change can affect. For a rename, notification
setting, or cadence-only update with no dependency, shared-resource, overlap, or
replay implication, view the task, retain its prior definition, apply the exact
field change with unchanged fields preserved, and read it back. Missing run
history alone does not block such an update. Report only the applied change,
readback, and material unknowns.

When the change affects coordination or compatibility, treat it as a graph
operation:

1. Inspect upstream tasks, downstream tasks, shared resources, and known active
   runs. Snapshot the prior definitions and prepare a rollback.
2. Prepare backward-compatible consumer guards before changing a producer receipt
   or cycle protocol. Install them only with separate repository or workload
   authority.
3. Pause affected tasks when compatibility is uncertain. Pause stops new
   activations; it is not proof that active work has drained.
4. Establish quiescence from supported run evidence before an incompatible
   change. If active-run state is unknown, leave the tasks paused and do not
   delete them.
5. Apply one authorized change with the supported tool, read it back, compare it
   with the requested state, and audit the affected graph.
6. Roll back from the snapshot when readback, the first safe run, or downstream
   compatibility fails.

## Retire

Pause first, establish quiescence, confirm that no consumer needs the task, and
retain required outputs and run evidence. Clean exact worktrees or revoke exact
task-specific credentials or claims only with separate explicit authority.
Otherwise report those steps as pending. Delete the automation only after the user
explicitly authorizes deletion and the retention decision is clear. Do not
describe deletion as recoverable unless the supported surface proves it.

## Report

Report the requested and applied state, resolved stable IDs, preserved fields,
coordination mechanism, coverage gaps, readback result, validation evidence,
rollback state, and remaining unknowns. Never claim scheduler-level dependency,
locking, retry, timeout, catch-up, or timezone enforcement unless the current
supported surface exposes and verifies it.
