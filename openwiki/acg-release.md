---
type: Architecture Reference
title: "ACG Release: macOS"
description: Ownership, applicability, release flow, authorization boundaries, and validation for the instruction-only acg-release plugin and its current macOS skill.
tags: [architecture, plugins, release, acg-box, macos, github-releases, sparkle, signing, notarization]
openwiki:
  roles: [architecture, repository, workflow, security]
  change_kinds: [public-api, validation, documentation, release]
  source_paths: [plugins/acg-release/.codex-plugin/plugin.json, plugins/acg-release/skills/macos/SKILL.md, plugins/acg-release/skills/macos/references/standard.md, plugins/acg-release/skills/macos/agents/openai.yaml, .agents/plugins/marketplace.json]
  symbols: [acg-release, macos, acg-box, Developer ID Application, notarization, immutable stable tag, draft-first publication]
  test_paths: [Makefile.toml]
  invariants: [The plugin is instruction-only, the canonical GitHub owner must be acg-box, one macOS skill owns one canonical standard, target workflows remain repository-owned, and validation never implies publication authority.]
  validation_commands: [cargo make check]
---

# ACG Release: macOS

`plugins/acg-release/` contains the installed manifest, `macos` skill, invocation
metadata, and canonical release standard. It is instruction-only; target
repositories own executable release workflows and product-specific adapters.

Use the [skill](../plugins/acg-release/skills/macos/SKILL.md) for applicability
and task scope. Use the [standard](../plugins/acg-release/skills/macos/references/standard.md)
for release requirements. Its sections cover source and workflow policy, secret
topology, signing, final assets, publication, trust-root changes, and acceptance.
Read the sections relevant to focused work, or the whole standard for a complete
release audit, migration, or operation.

Change runtime policy in those source files. The manifest and
`agents/openai.yaml` describe the public invocation `$acg-release:macos`; the
marketplace resolves the plugin at `./plugins/acg-release`. Keep those surfaces
consistent when changing discovery or applicability.

See [Operations](operations.md) for validation and installation. This wiki page
provides repository navigation; release policy remains in the canonical standard.
