---
type: Architecture Reference
title: Automation
description: Automation guidance, read-only analysis, compatibility, and development ownership.
tags: [automation, plugins, scheduled-tasks]
verified:
  - by: openwiki/0.7.2
    at: 2026-10-10T15:38:28.648Z
sources:
  - id: openwiki-source-40fe47491dcd7879819933ac
    resource: repo://dev/plugins/automation/README.md
  - id: openwiki-source-8c2e488cb190ab33220905a0
    resource: repo://plugins/automation/.codex-plugin/plugin.json
  - id: openwiki-source-028831b25ab82c7bc81127b4
    resource: repo://plugins/automation/scripts/audit_portfolio.py
  - id: openwiki-source-cc04ba3e4a886412ac32f960
    resource: repo://plugins/automation/skills/audit/SKILL.md
  - id: openwiki-source-3ae430141394067eba728e24
    resource: repo://plugins/automation/skills/manage/SKILL.md
generated: { by: "codex", at: "2026-10-10T15:38:28.648Z" }
---

# Automation

`plugins/automation` owns two skills: `audit` for read-only review and `manage`
for explicitly authorized changes to Codex Scheduled tasks. Simple reminders
and independent follow-ups use the live tool defaults. Coordination guidance
applies when tasks have dependencies, shared writers, or replay risks.

The plugin does not implement a scheduler, locks, leases, or fencing. Workload
and platform owners supply those guarantees. Read the skills and their linked
references for the canonical rules.

`scripts/audit_portfolio.py` analyzes a normalized snapshot from a selected file
or standard input. It reports dependency cycles, shared writers, timing conflicts,
and evidence gaps to standard output. It does not discover live tasks or mutate
a scheduler. The `helixbox/automation-*` schema identifiers remain unchanged so
existing snapshots stay compatible after the migration from `itering/exp`.

Development tests, synthetic fixtures, and benchmark tools live under
`dev/plugins/automation`. Historical evaluation results remain in the source
repository and were not imported. Run `cargo make test-automation` for local
contract and behavior checks; these checks do not establish live scheduler safety.

Install `automation@acg-box` from the Agentry marketplace. Migrating the plugin
does not change existing scheduled tasks. See [Operations](operations.md) and
[Privacy](../PRIVACY.md).
