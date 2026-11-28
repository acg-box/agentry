---
type: Architecture Reference
title: "ACG Release: macOS"
description: Ownership, applicability, release flow, authorization boundaries, and validation for the instruction-only acg-release plugin and its current macOS skill.
tags: [architecture, plugins, release, acg-box, macos, github-releases, sparkle, pkg, signing, notarization]
openwiki:
  roles: [architecture, repository, workflow, security]
  change_kinds: [public-api, validation, documentation, release]
  source_paths: [plugins/acg-release/.codex-plugin/plugin.json, plugins/acg-release/skills/macos/SKILL.md, plugins/acg-release/skills/macos/references/standard.md, plugins/acg-release/skills/macos/agents/openai.yaml, .agents/plugins/marketplace.json]
  symbols: [acg-release, macos, acg-box, Developer ID Application, notarization, immutable stable tag, draft-first publication]
  test_paths: [Makefile.toml]
  invariants: [The plugin is instruction-only, the canonical GitHub owner must be acg-box, one macOS skill owns one canonical standard, target workflows remain repository-owned, and validation never implies publication authority.]
  validation_commands: [cargo make check]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-28T16:28:40.721Z
sources:
  - id: openwiki-source-333c987ac700e02719816f1f
    resource: repo://plugins/acg-release/skills/macos/references/standard.md
  - id: openwiki-source-d2e490658308bc4b4744931f
    resource: repo://plugins/acg-release/skills/macos/SKILL.md
generated: { by: "codex", at: "2026-11-28T16:28:40.721Z" }
---

# ACG Release: macOS

`plugins/acg-release/` contains the installed manifest, `macos` skill, invocation
metadata, and canonical release standard. It is instruction-only; target
repositories own executable release workflows and product-specific adapters.

Use the [skill](../plugins/acg-release/skills/macos/SKILL.md) for applicability
and task scope. Use the [standard](../plugins/acg-release/skills/macos/references/standard.md)
to choose the Sparkle ZIP procedure or the target repository's installer PKG
procedure. Both use the same recovery section when Apple's notary service
reports a missing agreement or an interrupted submission. The PKG procedure
supports a local publisher when the target repository defines one.

Change runtime policy in those source files. The manifest and
`agents/openai.yaml` describe the public invocation `$acg-release:macos`; the
marketplace resolves the plugin at `./plugins/acg-release`. Keep those surfaces
consistent when changing discovery or applicability.

See [Operations](operations.md) for validation and installation. This wiki page
provides repository navigation; release policy remains in the canonical standard.
