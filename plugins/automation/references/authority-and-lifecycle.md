# Authority and Lifecycle

This reference owns shared capability, evidence, coverage, and lifecycle detail
for Codex automation governance. Read it only when the active audit or management
step needs those details. It does not grant mutation authority; the
`manage` workflow owns mutation authorization and execution.

## Capability Authority

Use the current supported automation-management tool and the official
[Scheduled tasks documentation](https://learn.chatgpt.com/docs/automations) as
the capability authority. Discover the live tool contract before each management
operation. Product surfaces can differ and can change.

Codex documents schedules, standalone and same-chat tasks, local and worktree
execution, status and recent-run review, unattended permissions, skills and
plugins, prompt testing, and early-run review. Do not infer undocumented behavior
for dependency order, shared-resource locking, concurrency limits, overlap,
backpressure, retry, timeout, missed-run recovery, timezone evaluation, or atomic
changes across a group of tasks. If the current tool does not expose a control,
record it as `application-enforced`, `externally-enforced`, or `unknown`.

This plugin is guidance. It does not add a scheduler, queue, lock service,
database, daemon, or cross-scheduler control plane.

## Scope and Coverage

No single observed source proves a complete automation portfolio unless that
source has a documented complete-list contract for every surface in scope. Every
audit must record:

- observation time;
- enumeration sources and known stable IDs;
- included schedulers, devices, projects, threads, and task types;
- excluded or unavailable surfaces;
- run-history window and evidence freshness;
- fields that are declared, observed, inferred, or unknown.

Call the result a `scoped audit` when complete enumeration is unavailable. Do not
claim global duplicate absence, complete dependency coverage, or global drift from
a scoped audit. A user declaration can fill a contract gap, but it remains
declared evidence until observed.

Follow the live tool's own inventory instructions. A local definition file can be
useful diagnostic evidence when the tool directs its use. An internal database or
file layout is not a stable public control API. Never mutate it.

## Evidence Labels

- `observed`: directly read from a supported surface or run record, with time.
- `declared`: supplied by an owner or checked-in workload contract.
- `inferred`: derived from a prompt, name, target, or behavior. State the reason
  and confidence.
- `unknown`: material evidence is missing, contradictory, stale, or outside the
  reachable surface.

Names and schedules do not prove dependency, duplication, or conflict. A clustered
start is a possible collision window. Actual overlap needs start and finish
evidence. Harm needs a shared effect, exhausted capacity, or failed contract.

## Lifecycle Gates

### Design

Define the task contract and the graphs needed for its coordination risks before
activation. The `manage` workflow selects prompt validation: safe preview,
applicable existing evidence, or authorized workload execution. Match that evidence
to the intended model, tools, permissions, target, and execution environment;
retain untested behavior and required activation evidence as separate gaps.

### Stage

For a change that needs staged activation, create paused when the current surface
supports it. Simple reminders and independent read-only follow-ups use the
`manage` fast path and current tool defaults. Read back the definition. If
paused creation is unavailable, disclose the immediate-activation risk.

### Activate and Observe

Activate one new dependency edge, shared-writer change, or incompatible protocol
change at a time. Review the first runs. Observe outcomes and side effects, not
only scheduler wakeups.

### Change

Snapshot prior definitions and prepare rollback. Prepare consumer compatibility
before changing producer output or receipt protocols. Apply it only with separate
repository or workload authority. A pause blocks new activations but does not prove
quiescence. Establish that active work has drained from supported evidence before
an incompatible change. Related mutations are not atomic unless the current
surface proves that they are.

### Retire

Pause, establish quiescence, and preserve required run evidence and outputs.
Remove or migrate consumers, clean exact worktrees, or revoke exact task-specific
access only with separate explicit authority. Otherwise report those steps as
pending. Delete the automation only with explicit authority and a clear retention
decision. If active-run state is unknown, leave the task paused.
