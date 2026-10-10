---
type: Operations Guide
title: Install And Validation
description: Installation, repository checks, plugin validation, CI behavior, and release boundaries for repository plugins.
tags: [operations, validation, plugins, github-settings, acg-release, macos-release, release]
openwiki:
  roles: [operations, testing, delivery]
  change_kinds: [validation, public-api, release]
  source_paths: [Makefile.toml, .taplo.toml, .github/workflows/check.yml, .agents/plugins/marketplace.json, plugins/acg-release/.codex-plugin/plugin.json, VERSION, PRIVACY.md]
  symbols: [check, check-json, fmt-check, Check, acg-release, macos, acg-box]
  test_paths: [Makefile.toml, .github/workflows/check.yml]
  invariants: [The Check workflow runs the same cargo make check command as local validation.]
  validation_commands: [cargo make check]
sources:
  - id: openwiki-source-8e7150eb410f39fb723ea62d
    resource: repo://.agents/plugins/marketplace.json
  - id: openwiki-source-af1b995411f58f4a90794b96
    resource: repo://plugins/acg-release/.codex-plugin/plugin.json
  - id: openwiki-source-8c2e488cb190ab33220905a0
    resource: repo://plugins/automation/.codex-plugin/plugin.json
  - id: openwiki-source-76d8051b07974472959e6838
    resource: repo://plugins/gh-settings/.codex-plugin/plugin.json
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
  - id: openwiki-source-94e7bca26bc3525581ff6cdf
    resource: repo://VERSION
generated: { by: "codex", at: "2026-10-10T15:38:28.648Z" }
verified:
  - by: openwiki/0.7.2
    at: 2026-10-10T15:38:28.648Z
---

# Install And Validation

## Install

Add the Git marketplace and install the optional plugins:

```sh
codex plugin marketplace add acg-box/agentry --ref main
codex plugin add gh-settings@acg-box
codex plugin add acg-release@acg-box
codex plugin add automation@acg-box
```

The marketplace entries at `.agents/plugins/marketplace.json` resolve all three
local plugin sources. Installation is outside ordinary source validation; use a
fresh task to verify that Codex loaded a newly installed version.

## Repository Checks

Install `cargo-make` and Taplo, then run the canonical quiet repository check:

```sh
cargo make check
```

`Makefile.toml` composes `check-json`, `fmt-check`, and `test-automation`. `check-json` parses
`.agents/plugins/marketplace.json` and all three plugin manifests with Python's
standard library. `fmt-check` checks `.taplo.toml` and `Makefile.toml` with Taplo.
`test-automation` runs the migrated Python unit tests and package-boundary checks.
Tests use temporary local fixtures and do not access a real scheduler.
The check performs no install, deployment, or release work.

Apply TOML formatting only when needed:

```sh
cargo make fmt
```

## Plugin Boundary Checks

The upstream validators import PyYAML and should run from an isolated Python
environment that provides it. Do not copy either validator into this repository or
add a Python project solely to host the dependency:

```sh
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" \
  plugins/gh-settings
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  plugins/gh-settings/skills/sync
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" \
  plugins/acg-release
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  plugins/acg-release/skills/macos
```

Also validate `plugins/automation` and both of its skills, `audit` and `manage`.
Its `package` manifest extension is checked by the package-boundary tests.

Run the applicable plugin and skill validators when changing metadata or structure.
For `acg-release`, semantic review must also confirm that the marketplace name,
local source path, plugin name, `macos` skill, `$acg-release:macos` invocation,
canonical-owner applicability gate, default prompt, version, privacy URL, and
four-file runtime set agree. For every plugin, review the marketplace entry, plugin
manifest, skill metadata, canonical reference, and invocation metadata as one
installable boundary. Automation keeps synthetic fixtures and benchmark tools under
`dev/plugins/automation`, outside the installable runtime.

## CI And Release

The `Check` workflow in `.github/workflows/check.yml` runs on pull requests targeting
`main`, pushes to `main`, and merge queues. It grants `contents: read`, uses one
Ubuntu job with a five-minute timeout, installs pinned `cargo-make` and Taplo, and
runs `cargo make check`. Pull-request runs may be canceled when superseded; `main` runs
are not canceled.

`VERSION` is `0.1.2`. Change it and every plugin manifest together only for an explicit
release. This repository has no publication workflow. Full verification or plugin
installation does not authorize publishing, deploying, or changing CI policy.

The plugins' privacy boundary is documented in [`PRIVACY.md`](../PRIVACY.md).
Automation includes a local read-only analyzer; the other plugins contain
instructions only. All manifests point consumers to that policy.

## Change-Safety Matrix

| Change | Narrow check | Escalate when |
| --- | --- | --- |
| TOML task or formatting configuration | `cargo make check` | task names or workflow behavior changes |
| Plugin metadata or path | Plugin Creator validator plus `cargo make check` | marketplace or consumer installation changes |
| Skill front matter or invocation metadata | Skill Creator validator | a namespaced skill resolution changes |
| Standard guidance | Skill Creator validator | release version, public prompt, or install surface changes |
| CI workflow | `cargo make check` | permissions, triggers, action pins, or release behavior changes |
