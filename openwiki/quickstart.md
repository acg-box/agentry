---
type: Quickstart Guide
title: Repository Quickstart
description: Navigation for the ACG Box repository that publishes the quality-gates Codex plugin and its validation standards.
tags: [openwiki, repository, plugins, quality-gates]
openwiki:
  roles: [repository, workflow]
  change_kinds: [public-api, validation, documentation]
  source_paths: [README.md, AGENTS.md, .agents/plugins/marketplace.json]
  symbols: [quality-gates, design]
  test_paths: [.github/workflows/check.yml, Makefile.toml]
  invariants: [The plugin manifest, marketplace entry, and repository VERSION must describe the same installable release.]
  validation_commands: [makers check]
---

# Repository Quickstart

## What This Repository Is

`acg-box/exp` publishes small ACG Box engineering standards as Codex plugins. The
current product is `quality-gates`, an instruction-only skill for designing lean,
risk-based repository validation. Its canonical runtime guidance is the standard at
[`plugins/quality-gates/skills/design/references/standard.md`](../plugins/quality-gates/skills/design/references/standard.md).

The repository has no application, reusable package, executable, MCP server, or
checked-in test program. Installable runtime belongs under `plugins/`; maintainer
context belongs under `openwiki/`.

## Start Here

1. Read root [`AGENTS.md`](../AGENTS.md) for authority and work boundaries.
2. Read [Quality Gate Architecture](quality-gates.md) for ownership, runtime shape,
   and public-surface synchronization.
3. Read [Install And Validation](operations.md) for narrow checks and release limits.
4. Before changing quality-gate behavior, read the full [canonical standard](../plugins/quality-gates/skills/design/references/standard.md).

## Task Routing

| Change area or user intent | Relevant wiki page | Exact source entry points | Important symbols or types | Focused tests | Minimal validation command |
| --- | --- | --- | --- | --- | --- |
| Change quality-gate guidance | [Quality Gate Architecture](quality-gates.md) | `plugins/quality-gates/skills/design/SKILL.md`, `references/standard.md` | `design`, `check-fast`, `check`, `verify` | Skill Creator `quick_validate.py` | `python3 .../quick_validate.py plugins/quality-gates/skills/design` |
| Change plugin metadata or installability | [Quality Gate Architecture](quality-gates.md) | `plugins/quality-gates/.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `VERSION` | `quality-gates`, `acg-box`, `0.1.0` | Plugin Creator `validate_plugin.py` | `python3 .../validate_plugin.py plugins/quality-gates` |
| Change repository checks or formatting | [Install And Validation](operations.md) | `Makefile.toml`, `.taplo.toml` | `check`, `check-json`, `fmt-check` | `makers check` | `makers check` |
| Change CI triggers or release boundaries | [Install And Validation](operations.md) | `.github/workflows/check.yml`, `PRIVACY.md` | `Check`, `contents: read` | GitHub `Check` workflow | `makers check` |
| Update repository navigation | this page and linked concepts | `README.md`, `AGENTS.md`, `openwiki/` | repository ownership statements | Markdown link review | `makers check` |

The validator paths above are relative to `${CODEX_HOME:-$HOME/.codex}/skills/.system`
and require an isolated environment with PyYAML; see [Operations](operations.md).

## Backlog

No evidence-backed documentation area is currently deferred.
