---
name: audit
description: Audit Codex Scheduled tasks or recurring automations without changing them. Use when the user's request positively identifies a Codex Scheduled definition, recurring cadence, thread follow-up, monitor, reminder, stable task ID, run record, automation dependency, overlap, backlog, drift, retirement, or shared-resource coordination. For a generic review of named files, inspect those files first, then use this skill before completing the review if the evidence positively identifies any of those automation facts. Do not trigger it from a safety prohibition, rejected proposal, label, denial, or out-of-scope mention alone.
---

# Audit Automations

Keep this workflow strictly read-only. Do not create, update, pause, resume,
delete, or otherwise change an automation. Do not change a repository or an
external workload unless the user separately authorizes that change.

Load detail only for the question in scope:

- Read `../../references/authority-and-lifecycle.md` only when you assess
  portfolio coverage, evidence authority, control-plane drift, or lifecycle
  status.
- Read `../../references/contract-and-coordination.md` only when you assess
  dependencies, shared resources, overlap, backlog, replay, timing, or a receipt,
  claim, lease, or fencing contract.
- Read `../../references/portfolio-analysis.md` only when a large structured
  inventory can use repeatable graph, resource, and finite-window checks.

Do not load the authority or coordination reference for a simple readback whose
supported surface and requested fields already establish the answer.

## Simple Readback Or Coordination Audit

For a request limited to known task fields, resolve the stable ID with the current
supported inventory/view contract and return the requested observed values, source,
observation time, and material unknowns. Do not build graphs, enumerate unrelated
tasks, or produce the full audit report merely to answer a status or cadence query.
Missing evidence remains unknown; a narrow readback does not prove global safety
or completeness.

Use the audit model, analysis, and report below when the request or inspected
evidence requires dependency, shared-resource, overlap, replay, lifecycle, drift,
or portfolio analysis. One task can require that analysis. Keep it scoped to the
question and affected relationships; task count alone does not select the path.

## Establish Scope and Evidence

1. Find the current supported automation-management tool and follow its live
   inventory and view contract. Do not use a frozen copy of tool fields.
2. Use the Scheduled view, user-supplied definitions, run records, and declared
   workload contracts when they are available and authorized. Treat an internal
   file or database as best-effort diagnostic evidence, not as global authority.
   Never modify private scheduler storage.
3. Record the enumeration sources, known task IDs, observation time, included
   surfaces, excluded surfaces, and run-history window. If no stable list surface
   exists, call the result a scoped audit. Never claim portfolio completeness,
   duplicate absence, or global drift from a partial inventory.
4. Label each material statement as `observed`, `declared`, `inferred`, or
   `unknown`. Give inferred dependency and resource edges a reason and confidence.
5. Do not request, print, or persist secret values. Record only the permission,
   connector, identity, or secret name needed to evaluate the boundary.

## Build the Audit Model

For each known task, collect its stable ID, name, scheduler or surface, status,
owner, purpose, target, cadence, business-time meaning, execution environment,
permissions, reads, writes, idempotency domain, dependencies, expected runtime,
observed runtime, overlap and replay policy, notification owner, and retirement
condition. Mark missing fields instead of inventing them.

Build two separate graphs:

- A dependency graph for producer-to-consumer ordering and cycle identity.
- A shared-resource graph for repositories, files, databases, documents,
  accounts, quotas, connectors, or idempotency domains that can conflict.

When a large inventory is available as structured data, read
`../../references/portfolio-analysis.md` completely and use the packaged
`../../scripts/audit_portfolio.py` helper for repeatable graph, resource, and
finite-window checks. Normalize supported live-tool output into its strict input
contract and preserve every evidence label and unknown value. Use the helper's
grouped output as audit evidence, not as live enumeration or scheduler evidence.
If the inventory cannot be normalized without guessing, do not run the helper;
report the scoped manual-analysis limit instead.

## Analyze

When a review asks for `Accept`, `Change`, or `Defer`, use these meanings:

- Use `Accept` only when the current proposal can proceed as written.
- Use `Change` when a proposed current action cannot proceed as written. An
  asserted current-state claim that lacks supporting evidence must be corrected;
  missing evidence does not turn that current action into `Defer`.
- Use `Defer` only when the proposal contains no current action and the supplied
  evidence cannot decide the statement.

1. Find missing producers, cycles, fan-in joins, paused producers with active
   consumers, incompatible receipt versions, and consumers that do not fail
   closed. A shared start time is not dependency order.
2. Compare schedule windows with observed or declared runtime envelopes. Treat a
   clustered start as a possible capacity or conflict window. Treat it as actual
   overlap only when run evidence supports that conclusion.
3. Check the declared arrival policy when a prior run is still active: skip,
   coalesce, queue, replace, or parallel. Check backlog age, missed-run behavior,
   retry ownership, partial failure, replay safety, and overrun response.
4. Find shared writers without an idempotency boundary or enforceable ownership
   protocol. Do not describe a local lock as cross-worktree or cross-machine
   protection unless the evidence proves that scope.
5. Distinguish a scheduled wakeup from an external side effect. A guarded run
   that exits safely is not the same as a duplicate write.
6. Classify near-duplicates by target, side effects, and idempotency domain. A
   similar name, prompt, or time alone does not prove duplication.
7. Check business timezone, daylight-saving transitions, month-end, holidays,
   machine or app downtime, worktree cleanup, unattended permissions, and
   notification coverage. Mark undocumented scheduler semantics as unknown.
8. Reconcile declared and observed state. Report unmatched records as drift
   candidates until an authoritative readback proves their status.

## Report

Lead with severity-ordered findings. For each finding, give the affected task or
edge, evidence label, risk, smallest safe correction, and remaining uncertainty.
Then provide:

- the audit coverage receipt and evidence gaps;
- the dependency and shared-resource views;
- collision and backlog windows;
- lifecycle and control-plane drift candidates;
- a proposed change sequence, without applying it;
- the smallest next observation that can resolve each important unknown.

Route design or authorized changes to `$automation:manage`.
