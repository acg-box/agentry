---
name: audit-and-reconcile
description: Audit and reconcile GitHub Enterprise, organization, and repository Web UI settings with exact drift previews and scope-safe readback. Use when Codex must review GitHub repository features, pull request and merge settings, release immutability, rulesets, security and analysis controls, CodeQL, secret scanning, Dependabot, or parent-enforced governance, or must apply an explicitly approved repository settings profile without changing organization or enterprise authority.
---

# Audit And Reconcile GitHub Settings

Default to a read-only audit. Reconcile only when the user gives explicit mutation
authority for one exact GitHub target and profile.

Read [the governance standard](references/standard.md) completely before an audit,
preview, or mutation. Treat the target repository's instructions, GitHub plan,
parent controls, and current official GitHub documentation as higher authority for
live behavior.

## Work

1. Bind the GitHub host, authenticated identity, exact `owner/repository`, stable
   repository ID, visibility, permission, requested profile, and allowed scopes.
2. Check current official GitHub documentation through the environment's current-docs
   route. Map every Web UI label to a supported connector, CLI, REST, GraphQL, or UI
   control. Do not invent an API field for a UI-only setting.
3. Audit repository state and effective parent state. Separate repository-owned
   controls from organization- and enterprise-owned controls.
4. Show the exact drift preview from the standard before any write. Include every
   field, endpoint or UI control, destructive item, paid-product gate, skip, and
   unknown. A preview is not mutation authority.
5. If explicit authority already binds this exact target and profile, refresh state
   and apply only still-current drift. Otherwise stop after the preview.
6. Read every changed control back from its authoritative interface. Re-audit parent
   controls and report effective state, partial results, and honest gaps.

## Hard Boundaries

- Never mutate an enterprise or organization setting during a repository-scoped
  reconciliation.
- Never weaken, detach, bypass, or replace an inherited ruleset or enforced security
  configuration.
- Never enable a paid GitHub security product for a private or internal repository
  unless the user explicitly selects that product and accepts its billing scope.
- Treat GitHub Code Quality as a separate billable product. Do not infer authority
  to enable it from a request for CodeQL, code scanning, or a security baseline.
- List parent-inclusive and repository-only rulesets separately. Delete only exact
  repository-owned ruleset IDs that appeared in the approved preview.
- Use protected credential delivery declared by the active environment. Do not
  print, persist, request, or place credentials in repository files or commands.
- Prefer supported machine interfaces. Use the GitHub Web UI only for a setting with
  no sufficient supported machine route, after declared routes are exhausted and
  browser use is permitted. Do not start a new login without explicit authority.
- Treat a stale preview, changed target, changed visibility, changed parent control,
  changed product availability, or uncertain write result as a stop condition.

## Report

Report the bound target and identity, parent authority, exact before/desired/after
values, operations attempted, readback evidence, skipped paid or unavailable
controls, and remaining gaps. Do not claim effective compliance from a successful
request alone.
