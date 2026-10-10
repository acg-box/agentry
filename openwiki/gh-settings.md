---
type: Architecture Reference
title: GitHub Settings
description: Runtime ownership, organization and repository scope, safety boundaries, public surfaces, and validation for the instruction-only GitHub settings plugin.
tags: [architecture, plugins, github, settings, security]
openwiki:
  roles: [architecture, repository, workflow, security]
  change_kinds: [public-api, validation, documentation]
  source_paths: [plugins/gh-settings/.codex-plugin/plugin.json, plugins/gh-settings/skills/sync/SKILL.md, plugins/gh-settings/skills/sync/references/standard.md, plugins/gh-settings/skills/sync/agents/openai.yaml, .agents/plugins/marketplace.json]
  symbols: [gh-settings, sync, central-first authority, repository-scoped mode, merge-commit-only baseline, zero repository-owned rulesets, exact drift preview, free security baselines]
  test_paths: [Makefile.toml]
  invariants: [Audits are read-only by default, organization-wide mode uses supported organization controls, repository-scoped mode keeps organization state read-only, selected zero-local-ruleset profiles require a count of zero on every repository, and only attached or enforced parent configurations determine effective state.]
  validation_commands: [cargo make check]
verified:
  - by: openwiki/0.7.2
    at: 2026-10-10T13:00:35.168Z
sources:
  - id: openwiki-source-814cee67e5419784bb2251c3
    resource: repo://plugins/gh-settings/skills/sync/references/standard.md
  - id: openwiki-source-f2a9bda4df7b989ef8b9ce83
    resource: repo://plugins/gh-settings/skills/sync/SKILL.md
---

# GitHub Settings

`plugins/gh-settings/` contains the installed manifest, `sync` skill, invocation
metadata, and canonical governance standard for GitHub organizations and
repositories. It has no executable runtime.

Use the [skill](../plugins/gh-settings/skills/sync/SKILL.md) for task scope and the
[standard](../plugins/gh-settings/skills/sync/references/standard.md) for team
policy. For free-feature and cost-control requests, read the standard's
[Prevent Additional Charges](../plugins/gh-settings/skills/sync/references/standard.md#prevent-additional-charges)
section. The standard covers scope and authority, security profiles, dependency
submission, Dependabot defaults, rulesets, merge policy, other settings, and
reconciliation. Load the sections relevant to the requested profile; a complete
governance audit uses the whole standard.

Change policy in those runtime files. The manifest and `agents/openai.yaml`
describe `$gh-settings:sync`; the marketplace resolves the plugin at
`./plugins/gh-settings`. Keep those surfaces consistent when changing discovery.

See [Operations](operations.md) for validation and installation. GitHub's current
documentation and observed account state establish provider behavior; this page
is repository navigation, not a second governance standard.
