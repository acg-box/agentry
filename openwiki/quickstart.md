---
type: Quickstart Guide
title: Repository Quickstart
description: Navigation for the ACG Box repository that publishes small Codex engineering-standard plugins and their validation rules.
tags: [openwiki, repository, plugins, github-settings, quality-gates]
openwiki:
  roles: [repository, workflow]
  change_kinds: [public-api, validation, documentation]
  source_paths: [README.md, AGENTS.md, .agents/plugins/marketplace.json]
  symbols: [gh-settings, sync, quality-gates, design]
  test_paths: [.github/workflows/check.yml, Makefile.toml]
  invariants: [The plugin manifest, marketplace entry, and repository VERSION must describe the same installable release.]
  validation_commands: [cargo make check]
---

# Repository Quickstart

## What This Repository Is

`acg-box/exp` publishes small ACG Box engineering standards as Codex plugins. Both
current plugins are instruction-only:

- `gh-settings` audits GitHub governance, puts enforceable controls at the highest
  supported scope in organization-wide mode, keeps parent state read-only in
  repository-scoped mode, previews exact drift, and reconciles only explicitly
  approved changes. Its canonical standard is
  [`plugins/gh-settings/skills/sync/references/standard.md`](../plugins/gh-settings/skills/sync/references/standard.md).
- `quality-gates` designs lean, risk-based repository validation. Its canonical
  standard is
  [`plugins/quality-gates/skills/design/references/standard.md`](../plugins/quality-gates/skills/design/references/standard.md).

The repository has no application, reusable package, executable, MCP server, or
checked-in test program. Installable runtime belongs under `plugins/`; maintainer
context belongs under `openwiki/`.

## Start Here

1. Read root [`AGENTS.md`](../AGENTS.md) for authority and work boundaries.
2. Read [GitHub Settings](gh-settings.md) or
   [Quality Gate Architecture](quality-gates.md) for the plugin you are changing.
3. Read [Install And Validation](operations.md) for narrow checks and release limits.
4. Before changing runtime behavior, read the full canonical standard for the
   selected plugin.

## Task Routing

| Change area or user intent | Relevant wiki page | Exact source entry points | Important symbols or types | Focused tests | Minimal validation command |
| --- | --- | --- | --- | --- | --- |
| Change GitHub settings guidance | [GitHub Settings](gh-settings.md) | `plugins/gh-settings/skills/sync/SKILL.md`, `plugins/gh-settings/skills/sync/references/standard.md` | `sync`, central-first authority, exact drift preview, automatic dependency submission, free Dependabot baseline | Skill Creator `quick_validate.py` | `python3 .../quick_validate.py plugins/gh-settings/skills/sync` |
| Change quality-gate guidance | [Quality Gate Architecture](quality-gates.md) | `plugins/quality-gates/skills/design/SKILL.md`, `references/standard.md` | `design`, `check-fast`, `check`, `verify` | Skill Creator `quick_validate.py` | `python3 .../quick_validate.py plugins/quality-gates/skills/design` |
| Change plugin metadata or installability | [Install And Validation](operations.md) | `plugins/*/.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `VERSION` | `gh-settings`, `quality-gates`, `acg-box`, `0.1.0` | Plugin Creator `validate_plugin.py` | Run the validator for each changed plugin |
| Change repository checks or formatting | [Install And Validation](operations.md) | `Makefile.toml`, `.taplo.toml` | `check`, `check-json`, `fmt-check` | `cargo make check` | `cargo make check` |
| Change CI triggers or release boundaries | [Install And Validation](operations.md) | `.github/workflows/check.yml`, `PRIVACY.md` | `Check`, `contents: read` | GitHub `Check` workflow | `cargo make check` |
| Update repository navigation | this page and linked concepts | `README.md`, `AGENTS.md`, `openwiki/` | repository ownership statements | Markdown link review | `cargo make check` |

The validator paths above are relative to `${CODEX_HOME:-$HOME/.codex}/skills/.system`
and require an isolated environment with PyYAML; see [Operations](operations.md).

## Backlog

No evidence-backed documentation area is currently deferred.
