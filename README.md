<div align="center">

# exp

Small, reusable ACG Box engineering standards.

[![License](https://img.shields.io/badge/License-GPLv3%20only-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-experimental-f59e0b.svg)](VERSION)

</div>

## Available Standard

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
codex plugin add quality-gates@acg-box
```

The plugin has no hook, app, MCP server, credential, or writable runtime state.
Installation does not authorize repository changes, CI changes, releases, or
deployments. See the repository [privacy policy](PRIVACY.md).

## Repository Layout

| Path | Owner |
| --- | --- |
| `plugins/quality-gates/` | Installable plugin runtime |
| `openwiki/` | Repository context and maintainer operations |
| `.agents/plugins/marketplace.json` | Marketplace discovery |
| `Makefile.toml` | Repository-local validation commands |

There is no `apps/`, `packages/`, or `dev/` tree. Add one only when a real owner
and validation contract exist.

## Develop

Install `cargo-make` and Taplo, then run:

```sh
makers check
```

See [OpenWiki operations](openwiki/operations.md) for plugin and skill validation.
