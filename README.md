<div align="center">

# exp

A reusable ACG Box engineering standard.

[![License](https://img.shields.io/badge/License-GPLv3%20only-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-experimental-f59e0b.svg)](VERSION)

</div>

## Available Plugin

### GitHub Settings

`gh-settings` audits GitHub Enterprise, organization, and repository governance
without changing it by default. It puts each enforceable control at the highest
supported scope, separates central defaults from repository residuals, and shows the
exact planned fields or Web UI controls before an authorized reconciliation. It also
prevents implicit paid-product enablement and reads every changed setting back.
Its merge-commit-only baseline keeps merge commits enabled, disables squash and
rebase, and rejects conflicting linear-history rules.
Organization-wide mode is central-first and can require zero repository-owned
rulesets. Repository-scoped mode audits parent state but never widens authority to
change it.

Read the [canonical GitHub settings standard](plugins/gh-settings/skills/sync/references/standard.md)
or invoke `$gh-settings:sync` after installation.

## Install

Add this Git marketplace, then install the optional plugin:

```sh
codex plugin marketplace add acg-box/exp --ref main
codex plugin add gh-settings@acg-box
```

The plugin is instruction-only. It has no hook, app, MCP server, credential,
network client, or writable runtime state. Installation does not authorize GitHub
settings changes, repository changes, CI changes, releases, or deployments. See the
repository [privacy policy](PRIVACY.md).

## Repository Layout

| Path | Owner |
| --- | --- |
| `plugins/gh-settings/` | Installable GitHub settings runtime |
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
