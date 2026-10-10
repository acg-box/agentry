---
type: Quickstart Guide
title: Repository Quickstart
description: Navigation for the ACG Box repository that publishes small Codex engineering-standard plugins and their validation rules.
tags: [openwiki, repository, plugins, github-settings, acg-release, macos-release]
openwiki:
  roles: [repository, workflow]
  change_kinds: [public-api, validation, documentation]
  source_paths: [README.md, AGENTS.md, .agents/plugins/marketplace.json]
  symbols: [gh-settings, sync, acg-release, macos, acg-box]
  test_paths: [.github/workflows/check.yml, Makefile.toml]
  invariants: [The plugin manifest, marketplace entry, and repository VERSION must describe the same installable release.]
  validation_commands: [cargo make check]
sources:
  - id: openwiki-source-8e7150eb410f39fb723ea62d
    resource: repo://.agents/plugins/marketplace.json
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
generated: { by: "codex", at: "2026-10-10T15:38:28.648Z" }
verified:
  - by: openwiki/0.7.2
    at: 2026-10-10T15:43:04.178Z
---

# Repository Quickstart

## What This Repository Is

Agentry (`acg-box/agentry`) publishes small ACG Box engineering standards as Codex plugins. The repository currently provides three plugins:

- [`automation`](automation.md) owns Scheduled-task audit, management, and local snapshot analysis.
- [`gh-settings`](gh-settings.md) owns GitHub governance profiles.
- [`acg-release`](acg-release.md) owns the ACG Box macOS release standard.

Installable runtime belongs under `plugins/`; Automation includes a local
read-only Python analyzer. Its tests and synthetic benchmarks belong under
`dev/plugins/automation/`. Maintainer navigation belongs under `openwiki/`.

## Start Here

1. Read root [`AGENTS.md`](../AGENTS.md) for authority and work boundaries.
2. Read [GitHub Settings](gh-settings.md) or [ACG Release: macOS](acg-release.md)
   for the plugin you are changing.
3. Read [Install And Validation](operations.md) for narrow checks and release limits.
4. Before changing runtime behavior, read the relevant canonical sections for
   the selected plugin.

## Task Routing

| Change area or user intent | Relevant wiki page | Exact source entry points | Important symbols or types | Focused tests | Minimal validation command |
| --- | --- | --- | --- | --- | --- |
| Change Automation guidance or analysis | [Automation](automation.md) | `plugins/automation/`, `dev/plugins/automation/` | audit, manage, snapshot schema | Python unit and boundary tests | `cargo make test-automation` |
| Change GitHub settings guidance | [GitHub Settings](gh-settings.md) | `plugins/gh-settings/skills/sync/SKILL.md`, `plugins/gh-settings/skills/sync/references/standard.md` | `sync`, central-first authority, exact drift preview, automatic dependency submission, free Dependabot baseline | Skill Creator `quick_validate.py` | `python3 .../quick_validate.py plugins/gh-settings/skills/sync` |
| Change the ACG Box macOS release standard | [ACG Release: macOS](acg-release.md) | `plugins/acg-release/skills/macos/SKILL.md`, `plugins/acg-release/skills/macos/references/standard.md` | `acg-release`, `macos`, canonical owner `acg-box`, Developer ID, notarization, final Sparkle ZIP, draft-first publication | Skill Creator `quick_validate.py` | `python3 .../quick_validate.py plugins/acg-release/skills/macos` |
| Change plugin metadata or installability | [Install And Validation](operations.md) | `plugins/*/.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `VERSION` | `gh-settings`, `acg-release`, `acg-box`, `0.1.2` | Plugin Creator `validate_plugin.py` | Run the validator for each changed plugin |
| Change repository checks or formatting | [Install And Validation](operations.md) | `Makefile.toml`, `.taplo.toml` | `check`, `check-json`, `fmt-check` | `cargo make check` | `cargo make check` |
| Change CI triggers or release boundaries | [Install And Validation](operations.md) | `.github/workflows/check.yml`, `PRIVACY.md` | `Check`, `contents: read` | GitHub `Check` workflow | `cargo make check` |
| Update repository navigation | this page and linked concepts | `README.md`, `AGENTS.md`, `openwiki/` | repository ownership statements | Markdown link review | `cargo make check` |

The validator paths above are relative to `${CODEX_HOME:-$HOME/.codex}/skills/.system`
and require an isolated environment with PyYAML; see [Operations](operations.md).

## Backlog

No evidence-backed documentation area is currently deferred.
