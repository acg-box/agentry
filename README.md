<div align="center">

# exp

Small, reusable ACG Box engineering standards.

[![License](https://img.shields.io/badge/License-GPLv3%20only-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-experimental-f59e0b.svg)](VERSION)

</div>

## Available Plugins

### GitHub Settings

`gh-settings` audits GitHub Enterprise, organization, and repository
settings without changing them by default. It binds one repository, separates
parent controls from repository-owned drift, and shows the exact planned fields or
Web UI controls before an authorized reconciliation. It also prevents implicit paid
security-product enablement and reads every changed setting back.

Read the [canonical GitHub settings standard](plugins/gh-settings/skills/sync/references/standard.md)
or invoke `$gh-settings:sync` after installation.

### Quality Gates

`quality-gates` helps an agent design and simplify repository validation. Its
default model has three public gates:

- `check-fast` gives quick deterministic feedback.
- `check` validates changed scope or explicit owners.
- `verify` runs the complete pre-integration or pre-release contract.

The standard keeps distinct platform, safety, atomicity, rollback, migration,
artifact, and runtime evidence. It removes duplicate builds, duplicate assertions,
unrelated service closure, and retry-based masking.

Read the [canonical standard](plugins/quality-gates/skills/design/references/standard.md)
or invoke `$quality-gates:design` after installation.

## Install

Add this Git marketplace, then install the optional plugin:

```sh
codex plugin marketplace add acg-box/exp --ref main
codex plugin add gh-settings@acg-box
codex plugin add quality-gates@acg-box
```

Both plugins are instruction-only. They have no hook, app, MCP server, credential,
network client, or writable runtime state. Installation does not authorize GitHub
settings changes, repository changes, CI changes, releases, or deployments. See the
repository [privacy policy](PRIVACY.md).

## Repository Layout

| Path | Owner |
| --- | --- |
| `plugins/gh-settings/` | Installable GitHub settings runtime |
| `plugins/quality-gates/` | Installable plugin runtime |
| `openwiki/` | Repository context and maintainer operations |
| `.agents/plugins/marketplace.json` | Marketplace discovery |
| `Makefile.toml` | Repository-local validation commands |

There is no `apps/`, `packages/`, or `dev/` tree. Add one only when a real owner
and validation contract exist.

## Develop

Install `cargo-make` and Taplo, then run:

```sh
cargo make check
```

See [OpenWiki operations](openwiki/operations.md) for plugin and skill validation.
