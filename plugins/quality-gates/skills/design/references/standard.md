# Repository Quality Gate Standard

## Purpose

Use this standard to make repository checks simple, fast, and reliable. A gate is
useful only when it proves a current risk at the correct boundary.

The standard does not require a monorepo, a selector, a task graph framework, a
cache, or a specific CI provider. Add a mechanism only when current repository
evidence requires it.

## Public Gates

Expose no more than these three gate levels:

| Command | Purpose | Normal scope | Excluded work |
| --- | --- | --- | --- |
| `check-fast` | Quick local feedback | Changed files or explicit owners | Product builds, containers, migrations, deployment, broad integration |
| `check` | Merge-request evidence | Changed owner closure or explicit owners | Unaffected owner tests and release-only work |
| `verify` | Complete integration or release evidence | All declared owners and critical boundaries | Deployment and publication unless separately authorized |

`check-fast` can run formatting checks, syntax checks, type checks, and other cheap
deterministic checks. It must not be a second copy of `check`.

`check` selects existing named tasks. It does not hide lint or test behavior inside
new duplicate commands. A repository with one owner, or with a cheap complete
check, can make `check` a direct aggregate and omit a selector.

`verify` is predictable. It does not use changed-scope selection. Run it at the
declared merge queue, default-branch, release, or manual boundary. Do not run it
for every small local edit.

## Scope And Owner Selection

Use one selection authority.

1. Map paths to meaningful owners, such as a service, package, runtime, platform
   boundary, or repository tool.
2. Expand the selected owners through native dependency metadata. Use Cargo, npm,
   Nix, or another existing graph when it is authoritative.
3. Declare shared inputs. A lock file, toolchain, root build file, selector, or
   common configuration can select all affected owners.
4. Accept explicit owner selection for focused work and diagnosis.
5. Print the selected owners and tasks before execution.

Do not keep the same dependency edge in CI YAML, a selector, a task file, and a
second registry. One owner must define it.

Resolve changed files from an explicit base or the merge base. CI must fetch enough
history to resolve that base. If the base is missing, a path is unknown, or graph
evaluation fails, run the complete safe source-validation set. Do not silently
skip work.

GitHub `paths` and `paths-ignore` are trigger filters. They are not a dependency
graph. A required check that does not start can also block integration. Prefer one
required workflow and select work inside it.

## Evidence Value

Keep a contract only when it can fail for a distinct required reason. Record:

- the risk that it proves;
- its owner and platform;
- its inputs and invalidation boundary;
- the named task that runs it; and
- the broader gate that includes it.

Merge or delete a contract when another retained contract has the same inputs,
assertion, platform, and failure meaning. Common low-value cases are:

- a build that repeats an identical build only to prove compilation again;
- a contract test that only repeats the implementation's own table or schema;
- a smoke test that does not run the final artifact or cross a runtime boundary;
- a full service closure for a change that cannot reach those services; and
- a test retry that converts an unexplained failure into a green result.

Compile, test, and package one compatible graph once. Reuse the result only when
source, toolchain, features, target, profile, trust, and artifact identity match.

## Task Runner Structure

Group public tasks by action. Use names such as:

- Check: `check-fast`, `check`, `check-rust`, `check-typescript`, `verify`.
- Format: `fmt`, `fmt-check`, `fmt-rust`, `fmt-rust-check`.
- Lint: `lint`, `lint-fix`, `lint-rust`, `lint-fix-rust`.
- Test: `test`, `test-rust`, `test-runtime`.
- Build and smoke: `build-<owner>`, `smoke-<owner>`.

Keep compiler checks under `check-*`, Clippy and other policy diagnostics under
`lint-*`, tests under `test-*`, and builds under `build-*`. The public `check`
gate can select these named tasks. Mutating fixes never run from a read-only gate.

Use a simple aggregate until affected selection has measured value. A minimal
single-owner task file can be:

```toml
[tasks.check-fast]
dependencies = ["fmt-check", "check-static"]

[tasks.check]
dependencies = ["check-fast", "lint", "test"]

[tasks.verify]
dependencies = ["check", "build-release", "smoke-release"]
```

When several owners make `check` materially expensive, replace only its aggregate
body with one bounded selector. Keep the underlying task names unchanged.

## CI Mapping

Use the gate commands as CI contracts. Do not reconstruct their behavior in YAML.

- Pull request: run `check` and cancel superseded runs when repository policy
  permits it.
- Merge queue or default branch: run `verify` when that boundary owns complete
  integration evidence.
- Tag or release: run the declared release verification, then build each required
  artifact once. Publication remains a separate authorized action.

Keep permissions minimal and pin external actions to reviewed immutable commits.
Order cheap deterministic failures before expensive work when parallel evidence
does not have higher value.

Do not add a Docker build, system migration, or platform matrix to a change only
because CI can run it. Select it because the changed owner closure or release
boundary requires it.

## Reliability

Fix intermittent behavior at its owner boundary.

- Use isolated temporary paths and deterministic fixtures.
- Remove shared mutable state between tests.
- Bind time, random data, network, processes, and external services explicitly.
- Preserve the first failure. Do not add automatic test retries.
- Distinguish a product failure from missing tools, unavailable runners, and
  provider admission failures.
- Put native file identity, locks, signals, launch agents, and filesystem behavior
  on the native platform that owns the contract.

## Critical Boundaries

Affected validation can select these contracts when their owner or inputs change.
Complete verification retains them at the declared integration or release
boundary:

- macOS and Darwin behavior, including launchd or launch agents;
- atomic publication or switching and crash recovery;
- rollback to the previous valid state;
- owner, mode, link count, inode, canonical path, and lock behavior;
- signals, process lifetime, and runtime environment boundaries;
- migrations and compatibility across supported generations;
- security policy, privilege, secret-delivery, and trust boundaries; and
- final artifact startup, identity, architecture, and packaging.

Do not replace a native or destructive boundary with a mock and claim equal
coverage. Do not run a destructive boundary for an unrelated edit.

## Measurement

Record the same measures before and after a change:

- public gate and task count;
- jobs and runners started for each event;
- selected owner closure for representative changes;
- compile, build, container, migration, and target fan-out;
- cold and warm elapsed time where available; and
- failures, cancellations, retries, cache transfer, and artifact transfer where
  they are material.

Separate local and hosted evidence. One local run can prove the local command. It
does not prove hosted steady-state savings. Report hosted cost, energy, and carbon
as unmeasured without provider-matched evidence.

## Adoption Test

A design conforms when all answers are clear:

1. Which one command gives quick feedback?
2. Which one command validates the changed owner closure?
3. Which one command gives complete pre-integration or pre-release evidence?
4. Which source owns path and dependency selection?
5. What happens for an unknown path or missing base?
6. Which retained contract proves each critical risk?
7. Which duplicate or unrelated work was removed?
8. What measured result would cause rollback of the gate change?

If a repository cannot answer a question, fix that ownership gap before adding a
new framework, cache, profile, registry, or retry policy.
