---
type: Operations Guide
title: Install And Validation
description: Installation, repository checks, plugin validation, CI behavior, and release boundaries for the repository plugin.
tags: [operations, validation, plugin, github-settings, release]
openwiki:
  roles: [operations, testing, delivery]
  change_kinds: [validation, public-api, release]
  source_paths: [Makefile.toml, .taplo.toml, .github/workflows/check.yml, VERSION, PRIVACY.md]
  symbols: [check, check-json, fmt-check, Check]
  test_paths: [Makefile.toml, .github/workflows/check.yml]
  invariants: [The Check workflow runs the same cargo make check command as local validation.]
  validation_commands: [cargo make check]
---

# Install And Validation

## Install

Add the Git marketplace and install the optional plugin:

```sh
codex plugin marketplace add acg-box/exp --ref main
codex plugin add gh-settings@acg-box
```

The marketplace entry at `.agents/plugins/marketplace.json` resolves the local
plugin source. Installation is outside ordinary source validation; use a fresh task
to verify that Codex loaded a newly installed version.

## Repository Checks

Install `cargo-make` and Taplo, then run the canonical quiet repository check:

```sh
cargo make check
```

`Makefile.toml` composes `check-json` and `fmt-check`. `check-json` parses
`.agents/plugins/marketplace.json` and the `gh-settings` plugin manifest with
Python's standard library. `fmt-check` checks `.taplo.toml` and `Makefile.toml` with
Taplo. The check performs no compile, network, container, migration, install,
deployment, or release work.

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
```

Run the plugin and skill validators when changing metadata or structure.
Semantic review must also confirm that marketplace name, plugin name, source path,
skill name, namespace, default prompt, version, privacy URL, and runtime file set
agree. There are no package-build, generated-artifact, or integration-test layers in
the current tree.

## CI And Release

The `Check` workflow in `.github/workflows/check.yml` runs on pull requests targeting
`main`, pushes to `main`, and merge queues. It grants `contents: read`, uses one
Ubuntu job with a five-minute timeout, installs pinned `cargo-make` and Taplo, and
runs `cargo make check`. Pull-request runs may be canceled when superseded; `main` runs
are not canceled.

`VERSION` is `0.1.0`. Change it and the plugin manifest together only for an explicit
release. This repository has no publication workflow. Full verification or plugin
installation does not authorize publishing, deploying, or changing CI policy.

The plugin's privacy boundary is documented in [`PRIVACY.md`](../PRIVACY.md): it
contains instructions only and does not collect, transmit, or store user data. The
manifest points consumers to that policy.

## Change-Safety Matrix

| Change | Narrow check | Escalate when |
| --- | --- | --- |
| TOML task or formatting configuration | `cargo make check` | task names or workflow behavior changes |
| Plugin metadata or path | Plugin Creator validator plus `cargo make check` | marketplace or consumer installation changes |
| Skill front matter or invocation metadata | Skill Creator validator | a namespaced skill resolution changes |
| Standard guidance | Skill Creator validator | release version, public prompt, or install surface changes |
| CI workflow | `cargo make check` | permissions, triggers, action pins, or release behavior changes |
