---
type: Architecture Reference
title: GitHub Settings
description: Runtime ownership, safety boundaries, public surfaces, and validation for the instruction-only GitHub settings plugin.
tags: [architecture, plugins, github, settings, security]
openwiki:
  roles: [architecture, repository, workflow, security]
  change_kinds: [public-api, validation, documentation]
  source_paths: [plugins/gh-settings/.codex-plugin/plugin.json, plugins/gh-settings/skills/sync/SKILL.md, plugins/gh-settings/skills/sync/references/standard.md, plugins/gh-settings/skills/sync/agents/openai.yaml, .agents/plugins/marketplace.json]
  symbols: [gh-settings, sync, exact drift preview, free Dependabot baseline]
  test_paths: [Makefile.toml]
  invariants: [Audits are read-only by default, repository reconciliation cannot mutate or weaken organization or enterprise authority, and only attached or enforced parent configurations determine effective repository state.]
  validation_commands: [cargo make check]
---

# GitHub Settings

## Runtime Boundary

`plugins/gh-settings/` is the complete installed runtime. It contains one
`sync` skill, invocation metadata, and one canonical GitHub settings
standard. It has no executable, hook, app, MCP server, credential, network client,
or writable state.

The canonical standard owns target binding, parent-scope classification, the exact
drift preview, free Dependabot repository baseline, mutation authority,
private-repository billing gates, ruleset safety, UI fallback, and authoritative
readback. It distinguishes an attached or enforced parent configuration from an
unattached organization catalog entry, and it keeps delegated alert dismissal
behind its current repository prerequisites and paid-product gates. Do not copy
these rules into OpenWiki.

```mermaid
flowchart TD
    marketplace["marketplace entry"] --> plugin["plugin manifest"]
    plugin --> skill["sync skill"]
    skill --> standard["canonical GitHub settings standard"]
    standard --> currentDocs["current official GitHub docs"]
    standard --> target["target repository and parent evidence"]
```

## Ownership And Trigger

The plugin owns GitHub settings audit and explicitly authorized reconciliation. It
is independent from [Quality Gate Architecture](quality-gates.md), which owns
repository validation architecture; both are discovered and validated through the
shared repository operations boundary. The public invocation is
`$gh-settings:sync`.

Repository state is not source authority for organization or enterprise state. The
skill audits parent rulesets and security configurations read-only and uses
repository-level equivalents only when current GitHub behavior supports them.

## Public-Surface Change Recipe

A behavior change starts in `skills/sync/SKILL.md` or its canonical
standard. Keep these surfaces synchronized:

- `.agents/plugins/marketplace.json` owns discovery at
  `./plugins/gh-settings`.
- `.codex-plugin/plugin.json` owns plugin metadata and the `./skills/` entrypoint.
- `agents/openai.yaml` owns the invocation label and default prompt.
- `VERSION` and every plugin manifest use the same repository release version.
- `PRIVACY.md` owns the shared instruction-only privacy boundary.

GitHub APIs, UI controls, plans, and billing boundaries can change. The runtime
standard therefore requires current official documentation before live work instead
of treating a checked-in endpoint example as permanent authority.

## Validation

Run the Plugin Creator validator, the Skill Creator validator, and
`cargo make check`.
Review the physical runtime file set: only the manifest, skill, invocation metadata,
and canonical reference belong in the plugin. Run Plugin Eval when available.

When installation is in scope, install after repository checks and verify pickup in a
fresh Codex task. Installation does not prove that the task that performed the
install loaded the new runtime.
