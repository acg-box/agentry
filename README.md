<div align="center">

# Agentry

Skills, standards, and workflows for agents.

Agentry publishes ACG Box engineering practices as small, reusable Codex plugins.

[![License](https://img.shields.io/badge/License-GPLv3%20only-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-experimental-f59e0b.svg)](VERSION)

</div>

## Available Plugins

### GitHub Settings

`gh-settings` audits or reconciles GitHub governance against an authorized profile,
with central organization controls and repository-scoped operation.

Read the [canonical GitHub settings standard](plugins/gh-settings/skills/sync/references/standard.md)
or invoke `$gh-settings:sync` after installation.

### ACG Release

`acg-release` guides Developer ID-notarized Sparkle macOS ZIP releases for
repositories whose canonical GitHub owner is `acg-box`.

Read the [canonical ACG Box macOS release standard](plugins/acg-release/skills/macos/references/standard.md)
or invoke `$acg-release:macos` after installation.

### Automation

`automation` audits Codex Scheduled tasks and manages authorized lifecycle
changes. It includes a read-only analyzer for normalized portfolio snapshots.
Use `$automation:audit` or `$automation:manage` after installation.

## Install

Add this Git marketplace, then install the optional plugins:

```sh
codex plugin marketplace add acg-box/agentry --ref main
codex plugin add gh-settings@acg-box
codex plugin add acg-release@acg-box
codex plugin add automation@acg-box
```

The release and GitHub settings plugins contain instructions only. Automation
also includes a local read-only analyzer. The plugins have no hook, app, MCP
server, bundled credential, or network client. Installation does not
authorize GitHub settings changes, repository changes, CI changes, releases, or
deployments. See the repository [privacy policy](PRIVACY.md).

## Repository Layout

| Path | Owner |
| --- | --- |
| `plugins/gh-settings/` | Installable GitHub settings runtime |
| `plugins/acg-release/` | Installable ACG Box release-standard runtime; current `macos` skill only |
| `plugins/automation/` | Automation guidance and read-only portfolio analyzer |
| `dev/plugins/automation/` | Synthetic fixtures, tests, and benchmark tools |
| `openwiki/` | Repository context and maintainer operations |
| `.agents/plugins/marketplace.json` | Marketplace discovery |
| `Makefile.toml` | Repository-local validation commands |

There is no `apps/` or `packages/` tree. Development assets stay outside the
installed plugin directories.

## Develop

Install `cargo-make` and Taplo, then run:

```sh
cargo make check
```

See [OpenWiki operations](openwiki/operations.md) for plugin and skill validation.
