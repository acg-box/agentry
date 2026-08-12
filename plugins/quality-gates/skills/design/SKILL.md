---
name: design
description: Design and simplify repository quality gates with risk-based layering and affected-scope defaults. Use when Codex needs to audit slow or flaky checks, remove duplicate builds or tests, reduce unrelated monorepo fan-out, design changed-scope or owner selection, structure task runners or CI gates, or preserve critical integration and release evidence.
---

# Design Quality Gates

Build the smallest validation graph that proves the repository's current risks.
Optimize the work that runs, not the number of configuration lines.

Read [the standard](references/standard.md) completely before a material design or
implementation. The target repository's instructions, source, tests, release
policy, and platform contracts remain authoritative.

## Work

1. Inventory every public task, workflow, trigger, job, build, test, platform,
   release lane, and caller. Include dormant and tag-only lanes.
2. Record the current command graph, affected owner closure, build fan-out, and
   elapsed time that is available. Mark hosted or platform evidence as unmeasured
   when it is not available.
3. Name each required risk and the one contract that proves it. Remove or merge a
   contract only when it has no independent failure evidence.
4. Design three public gates: quick feedback, affected validation, and complete
   verification. Keep action-first format, lint, test, build, and smoke task names.
5. Use changed scope or explicit owners only when the repository has more than one
   meaningful owner and selection avoids material work. Otherwise use a simple
   aggregate.
6. Implement the smallest accepted slice. Keep selector policy in one owner and
   reuse native dependency metadata where possible.
7. Run focused checks while editing. Run one complete verification only when it is
   proportionate to the changed risk and completion claim.

## Hard Boundaries

- Never use a retry to hide an unexplained test or infrastructure failure.
- Do not use provider path filters as the repository dependency graph.
- Unknown paths, missing bases, or selector failures must select the complete safe
  source-validation set.
- Do not make daily source checks build containers, run system migrations, deploy,
  or close over every service unless the changed risk requires that work.
- Keep Darwin or other platform-native behavior on its real platform.
- Keep distinct atomic publication, rollback, permission, identity, lock, signal,
  migration, artifact, security, and runtime-boundary evidence.
- Full verification validates. It must not deploy or publish unless a separate
  repository contract and user authority permit that action.

## Report

Report the old and new public commands, owner and dependency selection, contracts
kept or removed, task/job/build fan-out, measured elapsed time, and unverified
platform or hosted boundaries. Do not claim measured savings from configuration
shape or one unmatched run.
