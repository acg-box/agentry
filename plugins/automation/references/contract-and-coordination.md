# Contract and Coordination

This reference defines the minimum task record and the control patterns for
dependencies, shared resources, piled-up execution, replay, and mixed schedulers.
Read it only when one of those risks exists.

## Owner Boundary

Automation owns risk classification, contract selection, and
automation-definition coordination. It does not implement workload guarantees.
The workload or platform owner must implement and validate output/receipt
atomicity, join gates, idempotency keys, transactional claims, leases, fencing
tokens, and target-enforced stale-writer rejection under separate authority.

Record that owner and its native evidence. Do not require another plugin or
workload to adopt Automation vocabulary. Do not change workload or
platform code under automation-management authority.

## Core Task Record

Record each field. Use `not applicable` or `unknown` when that is the accurate
value.

| Area | Required record |
| --- | --- |
| Identity | Stable task ID, name, owner, purpose, scheduler or surface, target project or thread |
| Time | Cadence, business timezone and business-date meaning, daylight-saving expectation |
| Execution | Local or worktree environment, permissions, tools, connectors, model, and reasoning policy |
| Effects | Reads, writes, irreversible effects, resource group, and idempotency domain |
| Dependency | Producers, consumers, cycle key, input and output version, and freshness rule |
| Runtime | Expected and high-percentile runtime, deadline, overrun response, and cost or quota limit |
| Arrival | Overlap policy: skip, coalesce, queue, replace, or parallel; maximum backlog age |
| Failure | Retry owner, missed-run or catch-up policy, partial-failure behavior, checkpoint, and replay safety |
| Operations | Outcome record, notification and escalation owner, retention, rollback, and retirement condition |

Keep the record lightweight for an independent read-only task. Add receipt, join,
lease, or fencing details only when the corresponding dependency or shared-writer
risk exists.

## Use Two Graphs

The dependency graph answers: "Which successful output must exist for this cycle?"
The shared-resource graph answers: "Which tasks can interfere even when neither
depends on the other?" Keep these graphs separate. A time graph is useful for
capacity, but it does not replace either correctness graph.

Reject dependency cycles unless one node is explicitly a bounded feedback loop
with a stop rule and a new cycle identity. For fan-in, require every producer for
the same cycle and compatible versions before the join can proceed.

## Select the Smallest Sufficient Control

| Combination | Default control |
| --- | --- |
| Independent and resource-disjoint | Permit parallel execution when capacity and quota allow it. |
| Independent with shared capacity only | Spread starts from observed runtime and quota evidence; define backlog behavior. |
| Producer and consumer | Combine sequentially when lifecycle and replay semantics match; otherwise use a guarded handoff. |
| Shared writer without dependency | Use idempotency plus a target-enforced claim or serialize activation. |
| Dependency plus shared writer | Use both the guarded handoff and writer protocol; spacing is only a capacity aid. |
| Hard guarantee across systems | Use an external orchestrator or durable control plane that owns the guarantee. |

Do not require a dependency graph, receipt, or mutex for an independent task that
does not have that risk.

## Guarded Handoffs

Use a stable occurrence or business-cycle key. A producer can publish a success
receipt only after its output commits. The receipt should carry producer identity,
cycle, input version, output version or hash, success state, and commit time. A
consumer must verify the same cycle, compatible versions, and freshness and must
fail closed on missing, stale, ambiguous, or conflicting state.

A receipt and output have a strong atomic guarantee only when the system commits
them in one transaction. If they cross systems, use a verified commit protocol or
label the result ambiguous. A timestamp or TTL alone does not prove that the
receipt describes the correct input or committed output.

For fan-in, publish one receipt per producer and use a join gate. Never infer
success from a producer wakeup or from elapsed time.

## Shared Writers

Give each logical effect an idempotency key. Prefer a transactional claim in the
system that owns the target data. If a lease is needed, include expiry and a
monotonic fencing token. The target must reject every write from an older token;
lease expiry by itself does not stop a stale writer.

A filesystem lock protects only processes that share and honor the same lock and
filesystem semantics. Do not treat it as protection across worktrees, machines, or
external services without evidence. When target-enforced claims or fencing are not
available, coalesce the work, permit only one active trigger owner, or route the
workflow to an external orchestrator.

## Overlap, Backlog, and Replay

Compare recurrence intervals with an observed runtime distribution. Use a
high-percentile runtime and explicit margin for capacity planning. Fixed offsets
reduce start bursts but do not prove non-overlap.

For each arrival while work is active, choose one policy: skip, coalesce, queue,
replace, or parallel. Define maximum backlog age, deadline, stuck-run response, and
whether a retry belongs to the current cycle or a later one. Treat scheduler
behavior as unknown when the current surface does not expose it.

A combined sequential task still needs partial-failure and replay rules. If step A
commits and step B fails, the next attempt must resume from a checkpoint or replay
step A idempotently. Combine steps only when they fit the runtime envelope and can
share one failure and recovery owner.

## Time and Availability

Record business timezone separately from the scheduler expression. Test
daylight-saving gaps and repeats, month-end, leap day, holidays, machine or app
downtime, and a schedule change during an active run. Record missed-run and
catch-up behavior as observed, application-enforced, externally-enforced, or
unknown.

Local tasks can require the machine, app, and project to remain available.
Worktrees isolate Git changes but need cleanup. Unattended tasks inherit a
permission boundary that must be narrow enough for their side effects.

## Outcome and Drift Record

For material runs, retain the task ID, cycle key, scheduled time, actual start and
finish, outcome, input and output version, dependency decision, writer decision,
side effects, retry count, and next owner. Distinguish `succeeded`, `failed`,
`skipped`, `blocked`, `stale`, `partial`, and `unknown`.

Reconcile declared and observed definitions, status, targets, and consumers.
Report unmatched or stale records as drift candidates until supported readback
proves their control-plane state.
