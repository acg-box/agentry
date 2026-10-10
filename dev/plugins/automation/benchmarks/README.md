# Automation Test Design

This test system has five separate evidence layers. Do not combine their claims.

## Layer 1: Source Contracts

The Python unit tests check runtime guidance, benchmark structure, prompt
neutrality, fixture coverage, hidden-oracle separation, runner isolation, scoring,
and claim labels. A pass proves only that the checked-in sources satisfy these
contracts. It does not prove that an agent follows the guidance.

## Layer 2: Deterministic Portfolio Analysis

The packaged `scripts/audit_portfolio.py` helper analyzes a normalized, finite
portfolio snapshot without model calls, network access, scheduler access, or
state changes. The blocking unit suite checks exact dependency components,
scope-aware missing producers, paused-producer edges, grouped shared-writer
risks, half-open schedule windows, capacity peaks, unknown evidence, input-order
invariance, small random differential oracles, and a 10,000-task pathological
portfolio. Shared-writer output is grouped by resource and bounded; it never
expands all task pairs.

This layer proves only deterministic classification of the supplied normalized
snapshot. It does not prove that a live inventory is complete, that resource
aliases are equivalent, or that a scheduler has the modeled overlap, capacity,
retry, catch-up, or queue behavior. A 10,000-task fixture validates the scale
path and grouped output bound. It is not a production-representativeness claim.

The helper uses an iterative Kosaraju pass because Python `graphlib` can reject a
cycle but cannot enumerate every exact cyclic strongly connected component. It
uses a half-open endpoint sweep for finite-window capacity. The repository has no
approved graph dependency that provides the same exact, deterministic,
bounded-output contract. The iterative traversal also avoids recursion failure
on long graphs.

Reassess these choices after an input-semantics or algorithm change. Replace a
local implementation if the supported Python standard library or an approved
existing dependency provides the same contract with lower net risk.

## Layer 3: Optional Paired Synthetic Behavior

The paired benchmark asks an auth-only no-skill home and a treatment home with
only the two candidate skill trees and shared references to review the same
synthetic proposals. It uses the same model, reasoning effort, prompts, fixtures,
sandbox, and approval policy. The prompt does not name the plugin, skills,
expected controls, or rubric. The oracle and coverage map are outside the
benchmark workspace and outside the command allowlist. This boundary hides them
from the model's permitted command surface. It is not cryptographic host
isolation.

This layer measures read-only audit routing and proposition classification.
Cases 01 through 10 must load `audit`; case 11 is the negative-routing
case. This layer does not measure `manage` activation, scheduler tool
calls, or mutation execution. Those claims need a separately authorized live
conformance test.

Routing observation is path-bound. A complete audit load requires successful
completed commands whose canonical audit `SKILL.md` path operands and exact
outputs collectively cover the complete frozen skill body. A command that reads
an unrelated path does not count, even when its output contains the same text.
Candidate-path identities are case-normalized because the benchmark can run on a
case-insensitive file system.
Any canonical access to either candidate skill or a shared candidate reference
counts as treatment access. Therefore, case 11 fails negative routing on any such
access. A failed command can establish access, but only a successful command
output contributes to a complete skill load. Case 04 also fails positive routing
if the manage skill is accessed, even when its full body is not loaded.

Both arms receive the same task-neutral file-access rule, whether or not they use
a skill. When an available skill is relevant, the model must use the exact
`SKILL.md` path from the available-skills inventory and resolve only its directly
linked references. The only accepted pipeline is
`rg --files PATH... | rg REGEX`. Its producer paths must resolve inside the
fixture workspace. Its consumer must have one non-option regex and no file
operand. Parent Codex-home scans, other pipelines or control chains, redirection,
and dynamic shell discovery fail closed.
Candidate routing also requires positive scheduled or recurring task scope. A
one-time database, data, schema, or code migration does not qualify when
automation terms appear only in a denial, label, or out-of-scope statement.

Every scenario produces one disposition for each labeled proposal. The runner
rejects missing, duplicate, invented, or malformed decisions. A wrong decision
on a `critical_ids` proposition is a treatment hard failure. Invalid treatment
output is also a treatment hard failure. The same control-arm mistakes are scored
as baseline behavior, with invalid control output receiving zero correct items;
they do not invalidate the experiment. A process failure, control contamination,
workspace change, or forbidden external-action event is an integrity failure in
either arm. Average accuracy cannot compensate for a treatment or integrity
failure.

This benchmark is optional research. Run it only when a claim about skill routing
or model-behavior improvement is needed. It is not a routine repository gate and
it does not validate a large automation portfolio. The 220 confirmation cells
are 11 synthetic scenarios times 10 paired repetitions times 2 arms; they are
not 220 automation definitions.

The benchmark has these phases:

- `smoke`: one counterbalanced pair per scenario. It checks only the harness.
- `pilot`: three pairs per scenario. Use it to find fixture or scorer defects.
  Exclude pilot results from effect claims.
- `confirm`: ten preregistered pairs per scenario. Do not filter scenarios or
  change the repetition count or preregistered seed (`94271`) for a confirmation
  result.

Run a no-token dry run first:

```sh
python3 dev/plugins/automation/scripts/run_behavior_benchmark.py \
  --phase smoke --dry-run
```

An authenticated run consumes real model tokens but uses only synthetic files:

```sh
python3 dev/plugins/automation/scripts/run_behavior_benchmark.py \
  --phase smoke \
  --output-dir /tmp/automation-smoke-v5

python3 dev/plugins/automation/scripts/run_behavior_benchmark.py \
  --phase pilot \
  --qualification-metadata /tmp/automation-smoke-v5/metadata.json \
  --output-dir /tmp/automation-pilot-v5

python3 dev/plugins/automation/scripts/run_behavior_benchmark.py \
  --phase confirm \
  --qualification-metadata /tmp/automation-pilot-v5/metadata.json \
  --output-dir /tmp/automation-confirm-v5
```

The pilot and confirmation accept only the runner-generated raw metadata from a
complete, clean, immediately preceding phase with the same frozen protocol,
candidate, fixtures, model configuration, seed, scenario set, and Codex CLI
identity. A manual evaluation receipt is not launch authority. A pilot or
confirmation dry run without qualifying metadata reports
`launch_authorized: false` and does not access authentication or invoke a model.
Dry runs use `smoke_schedule_only`, `pilot_schedule_only`, or
`confirmation_schedule_only`; they never emit a completed-run label.

The runner uses an auth-only control home, an auth-plus-candidate-skills treatment
home, an allowlisted process environment, a read-only sandbox, and disabled apps
and delegation. Before the first cell, it freezes one no-follow authentication
snapshot, one workspace snapshot, and one treatment snapshot. Every cell uses
those snapshots. The result records the runner, configuration, oracle, coverage,
workspace, plugin, and treatment digests. It does not record a credential digest.
A source or persistent Codex CLI identity change during the run blocks the phase
and causes a nonzero exit. It preserves raw Codex event logs outside the
disposable workspace.

Before it launches the next phase, the runner reopens the prior raw bundle. It
reparses each final message, reruns the event and routing guards, recomputes every
score and failure field, rebuilds the schedule and arm summaries, and checks all
per-cell artifact and bundle hashes. Confirmation also reopens the smoke bundle
named by the pilot's qualification provenance. A standalone JSON summary or a
copied manual receipt cannot qualify a run.

Verify a checked evaluation receipt against its raw bundle with:

```sh
python3 dev/plugins/automation/scripts/verify_evaluation_receipt.py \
  dev/plugins/automation/evaluations/RECEIPT.json \
  --raw-root /tmp/RAW-RUN-ROOT
```

The verifier requires legacy receipt schema 1 with raw schema 1, or receipt
schema 2 with protocol-v5 raw schema 2. Version 5 fails closed unless the current
source checkout has the runner, config, oracle, coverage, workspace, candidate,
and treatment digests bound by the receipt. This makes the verification
source-specific; it is not a portable signature and it does not authorize a new
run.

The event guard fails closed on malformed or unknown event records. The runner
seeds a restricted process `PATH`, uses a small command allowlist, and limits path
roots to the disposable fixture workspace and treatment skill/reference trees.
Trusted host login-shell startup files can extend the effective shell `PATH`.
The benchmark does not attest command-binary identities. Its shell scan is
quote-aware: regular-expression metacharacters in literal quotes remain
data. One bare pipeline is allowed only for
`rg --files PATH... | rg REGEX`, with workspace-confined producer paths and one
non-option consumer regex. Active expansion, grouping, other pipelines or control
chains, redirection, parent scans, and dynamic loops fail closed. Only exact
`/bin/bash`, `/bin/sh`, and `/bin/zsh` wrappers can be unwrapped. Explicit
executable paths must be exact allowlisted system binaries. The strict workspace
digest includes dot
directories, `__pycache__`, file modes, and symlink targets. For `sed` and `rg`,
only enumerated non-file options are allowed; compact, ambiguous, and unknown
options fail closed. Protocol version 5 rejects every `jq` command, including
module-loading filters. If the preflight cannot establish these controls, do not
run the benchmark.

For the one allowed pipeline, each producer operand must map to an existing,
readable, nonsymlink file or tree in the frozen workspace. The guard directly
replays the `rg --files` producer operands without a shell or ripgrep config and
requires a zero exit status. Qualification and receipt verification remap the
deleted per-cell path to the source-bound workspace with the same digest. This
prevents a successful consumer from hiding a failed producer. The replay uses
the current host `rg`; the benchmark still does not attest command-binary
identities.

Protocol version 5 retains protocol version 4's frozen qualification and CLI
identity chain and protocol version 3's read-only ripgrep `-g` and `--glob`
filename-filter repair. It resolves one canonical Codex executable,
captures a self-consistent version and entry hash before the schedule, checks the
identity again after the schedule, and requires a matching clean raw-metadata
chain from smoke to pilot to confirmation. These checks detect ordinary
persistent application updates. They do not detect a hostile executable that
changes and restores itself between checks, and they do not observe backend model
alias drift. Version 5 does not rewrite any earlier receipt. In particular, the
protocol-v4 pilot remains failed because one otherwise read-only control command
used a pipeline that version 4 prohibited.

Do not substitute a direct Plugin Eval benchmark for the paired runner. The
current Plugin Eval workspace provisioning exposes a local marketplace; it does
not by itself prove that the candidate skills were active. Use Plugin Eval static
analysis for plugin structure, and require observed treatment-only skill reads in
the paired behavior result.

The deterministic score is primary. For a broader qualitative statement about
the rationale, blind the outputs and use two independent reviewers with
`reviewer-score.schema.json`. Reviewers must not see the arm, target path, plugin
name, event log, or unblinding map. Double-score at least 20 percent of outputs.
Require Cohen's kappa of at least 0.80 for the binary fields. Record disagreements
and their adjudication.

A confirmation can support only a benchmark-local proposition-classification
effect. It requires all pairs, valid candidate outputs, zero candidate hard
failures, at least 90 percent candidate accuracy, no per-scenario regression, and
at least 10 percentage points of absolute uplift over the control. Candidate
over-control errors must be at most 5 percent of the preregistered over-control
items. The scenario-stratified paired bootstrap uses proposition-weighted
correct/total counts, 5,000 samples, the fixed seed, and a 95 percent interval.
Its estimate must equal the reported proposition-weighted accuracy uplift, and
its lower bound must be greater than zero. If the control is at or above 95
percent, report a control ceiling and make no improvement claim. Do not call the
result a general plugin pass.

This layer does not prove real inventory completeness, scheduler concurrency,
readback, pause or drain behavior, mutation safety, catch-up behavior, timezone
behavior, or cross-machine fencing.

## Layer 4: Deterministic Manage Contract

`scripts/manage_contract.py` is an in-memory control-plane contract
harness. It exercises explicit exact-target authority, paused creation, stable-ID
readback, requested-change preservation through full-field revision-fenced
updates, one activation receipt, pause without drain, supported quiescence
evidence, consumer and retention gates, exact-ID deletion, and target-enforced
fencing. A newer valid fencing token advances the target watermark even when the
logical effect is an idempotent replay or an idempotency conflict. Its negative
tests reject missing authority, duplicate creation or
rename, partial or lossy updates, stale revisions, unknown quiescence, incomplete
consumer or retention decisions, and unfenced or stale effect writers.

This harness does not call a real automation control plane. It does not run a
model, prove `manage` routing, verify a current tool schema, mutate a
Scheduled task, or establish scheduler behavior. A pass is source-contract and
synthetic workload-protocol evidence only. It does not replace the separately
authorized live canary. The in-memory target models one atomic durable
transaction. A production target must persist its idempotency records and highest
validated fencing token together and must authenticate the token issuer before it
can claim stale-writer exclusion or exactly-once effects.

## Layer 5: Live Control-Surface Conformance

`live-canary.md` defines an opt-in conformance check for the current Scheduled
surface. It is not an efficacy arm. It requires separate explicit authority for
the exact canary names and for create, activate, update, pause, and delete actions.
No live canary is part of `cargo make check` or the paired synthetic benchmark.

## Pre-Registered Falsifiers

Any of these results blocks the relevant positive claim:

- an audit mutation or unauthorized external action;
- a global coverage claim from partial evidence;
- schedule spacing used as dependency order or mutual exclusion;
- a non-atomic receipt treated as strong success evidence;
- a lease treated as protection against a stale unfenced writer;
- an update that loses an unchanged field or creates a duplicate;
- deletion without exact authority and the required lifecycle gates;
- material over-control of independent tasks;
- absent, negative, or unstable paired uplift;
- a live canary that contradicts a claimed current control-surface behavior.

Keep immutable raw results. After a fixture, scorer, model, or plugin change, make
a new run with new digests. Do not rewrite an earlier result.
