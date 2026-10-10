# Portfolio Analysis

Use the optional read-only analyzer when a large automation inventory is already
available as a normalized JSON snapshot. The analyzer does not enumerate a live
control plane. It does not parse cron or RRULE text. It does not create, update,
pause, resume, or delete an automation.

## Run the Analyzer

Resolve `../../scripts/audit_portfolio.py` from the active
`audit/SKILL.md` path. Pass an existing JSON file, or pass JSON on
standard input. The analyzer writes one JSON result to standard output and does
not write a file.

```sh
python3 /installed/plugin/scripts/audit_portfolio.py snapshot.json
```

Use only normalized task IDs, resource IDs, capacity groups, and occurrences.
Preserve each evidence label. Do not convert an `unknown` value to an empty list,
zero, or a safe control.

## Input Contract

Use `helixbox/automation-portfolio-snapshot/1` with these top-level fields:

- `coverage`: `kind`, observation time, enumeration sources, excluded surfaces,
  and the documented complete-list contract when `kind` is `complete`;
- `capacityGroups`: normalized capacity-group IDs, positive limits or `null`, and
  evidence labels;
- `resourcePolicies`: normalized resource IDs, idempotency-boundary and
  enforceable-ownership values, and evidence labels;
- `tasks`: unique stable IDs, status, dependency edges, write references,
  normalized schedule occurrences, arrival policy, and field evidence.

Use only `observed`, `declared`, `inferred`, or `unknown` as evidence labels. An
inferred dependency or write reference needs a reason and a confidence value from
0 to 1. Set `external` on a dependency only when its producer is intentionally
outside the portfolio and does not appear in the same snapshot. Use `null` for
unknown task lists, arrival policy, resource control, capacity, or occurrence end
time. An empty list means that the source declared that no item exists.

Each occurrence is a finite half-open window. It has `startEpochSeconds`, an
optional `endEpochSeconds`, positive `units`, and a `capacityGroup`. Normalize a
recurring schedule over an explicit audit horizon before analysis. Record that
horizon in the audit coverage receipt. Do not infer daylight-saving, missed-run,
catch-up, retry, queue, or concurrency behavior from these windows.

Example:

```json
{
  "schema": "helixbox/automation-portfolio-snapshot/1",
  "coverage": {
    "kind": "scoped",
    "observedAt": "2026-07-22T12:00:00Z",
    "sources": ["supported Scheduled task list"],
    "excludedSurfaces": ["offline device"],
    "completeListContract": null
  },
  "capacityGroups": [
    {"id": "local", "limit": 2, "evidence": "declared"}
  ],
  "resourcePolicies": [
    {
      "resource": "repo:example/main",
      "idempotencyBoundary": true,
      "enforceableOwnership": false,
      "evidence": "declared"
    }
  ],
  "tasks": [
    {
      "id": "task-a",
      "status": "active",
      "dependencies": [],
      "writes": [
        {"resource": "repo:example/main", "evidence": "declared"}
      ],
      "occurrences": [
        {
          "capacityGroup": "local",
          "startEpochSeconds": 1784725200,
          "endEpochSeconds": 1784727000,
          "units": 1,
          "evidence": "declared"
        }
      ],
      "arrivalPolicy": "coalesce",
      "evidence": {
        "identity": "observed",
        "status": "observed",
        "dependencies": "declared",
        "writes": "declared",
        "occurrences": "declared",
        "arrivalPolicy": "declared"
      }
    }
  ]
}
```

The parser rejects unknown or duplicate JSON object fields, duplicate stable IDs,
duplicate resource or capacity policies, malformed windows, in-snapshot producers
marked as external, and inferred dependency or write edges without a reason and
confidence value. This fail-closed behavior prevents an input typo from becoming
an apparent safe result.

## Result And Complexity

The analyzer reports exact cyclic strongly connected components, grouped
out-of-snapshot producers, grouped paused-producer edges, grouped shared-writer
risks, same-start clusters, normalized-window capacity excess, and grouped
evidence gaps. Risk groups include evidence-label counts and bounded member
samples so the audit can join sampled IDs back to the normalized input when it
needs edge reasons or confidence. Keep the input snapshot with the audit receipt.
The analyzer never expands all task pairs for one shared resource.

The strongly connected component pass is `O(V + E)` after normalization. Stable
input and output ordering makes the full dependency path
`O((V + E) log(V + E))` in the worst case. Grouping write references is linear,
and stable resource and member sorting makes the full shared-writer path
`O(R log R)` in the worst case, plus grouped output. The schedule pass is
`O(W log W)` for the supplied finite occurrences. A dense graph can still have
`E` proportional to `V` squared. A large recurrence horizon can also produce
many occurrences.

Treat a same-start cluster as a possible capacity window. Treat a capacity result
as a property of the normalized supplied windows and declared capacity. Neither
result proves actual run overlap or scheduler behavior. A paused-producer result
requires a separate freshness check. A dependency cycle requires a separate
bounded-feedback review.

Every result uses `normalizedSnapshotAnalysisOnly`. It cannot support a global
conflict-free claim. It does not prove live inventory completeness, resource
alias equivalence, scheduler semantics, model routing, or mutation safety. When
coverage is scoped, a producer that is not in the snapshot can still exist on an
excluded or unavailable surface.
