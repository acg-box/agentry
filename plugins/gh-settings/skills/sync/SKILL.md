---
name: sync
description: Audit and reconcile GitHub Enterprise, organization, and repository governance with central-first organization-wide authority, safe repository-scoped operation, exact drift previews, paid-product safety, and effective-state readback. Use when Codex must govern account-wide security configurations and defaults, rulesets, repository policies, release immutability, web commit signoff, Projects, Actions, Code Quality access, Dependabot controls, repository features, pull-request and merge settings, or one exact repository profile.
---

# Sync GitHub Governance

Default to a read-only audit. Reconcile only when the user gives explicit mutation
authority for the exact GitHub targets, scopes, and profile.

Read [the governance standard](references/standard.md) completely before an audit,
preview, or mutation. Treat target repository instructions, GitHub plan and billing
state, parent controls, and current official GitHub documentation as higher
authority for live behavior.

## Central-First Authority

Select the operating mode from the user's authority.

In organization-wide mode, put each control at the highest GitHub scope that can
provide the required outcome:

1. Enterprise enforcement;
2. organization enforcement;
3. organization or Enterprise default with explicit repository override
   precedence; or
4. repository state only when GitHub has no sufficient parent control.

Do not duplicate repository settings when an enforced parent supplies the outcome.
Do not call a default enforcement. In repository-scoped mode, keep parent state
read-only and reconcile only the exact repository.

## Work

1. Bind the operating mode, GitHub host, authenticated identity, Enterprise,
   organization, plan, target repository inventory, requested profile, and allowed
   mutation scopes.
2. Check current official GitHub documentation through the environment's
   current-docs route. Map each control to a supported connector, CLI, REST,
   GraphQL, or UI interface.
3. Audit Enterprise and organization controls, central defaults, effective
   repository attachments, parent-inclusive rulesets, repository-owned rulesets,
   runner prerequisites, and repository residuals.
4. Classify each control as Enterprise-enforceable, organization-enforceable,
   central default, repository-only, or paid/unavailable.
5. Show the standard's exact drift preview before any live write. Include every
   changed field, endpoint or UI control, paid gate, conditional change, and exact
   destructive object.
6. Refresh state. Apply only still-current approved drift. For a `migrate`
   decision, create and verify the parent replacement before local deletion. For
   an explicit `retire` decision, verify the accepted parent baseline first.
7. Read every changed control back from its authoritative interface. Re-audit
   effective state for every repository after parent changes.

## Hard Boundaries

- Never broaden mutation authority from repository to organization or Enterprise,
  or from organization to Enterprise.
- Never weaken, detach, bypass, or replace an inherited rule or enforced security
  configuration without exact authority for that parent object.
- Never enable Code Security, Secret Protection, Code Quality, or another paid
  product for a private or internal repository without explicit product and
  billing authority.
- Treat Code Quality as separate from CodeQL and Code Security. For a requested
  `No repositories` policy, do not start scans or accept charges to configure it.
- Keep Dependabot on the standard GitHub runner unless an exact eligible runner and
  label exist. Do not create a runner or select one that can queue indefinitely.
- Preserve `dependabot.yml` and repository-override precedence for organization
  defaults such as grouped security updates.
- Diagnose failed security configuration attachments. Allow active advanced CodeQL
  setup when that is the safe way to preserve working public coverage.
- For a merge-commit-only profile, require merge commits, disable squash and
  rebase, and reject any effective `required_linear_history` conflict before
  activation.
- List parent-inclusive and repository-only rulesets separately. Delete only exact
  repository-owned IDs in the approved preview and only after effective parent
  replacement readback.
- When a zero-local-ruleset profile explicitly retires a repository rule, verify the
  accepted parent baseline and delete the exact ID. Do not invent a preservation
  team, role, app, or adapter for semantics the profile says to remove.
- Do not invent a team or role to replace a user-specific repository bypass. Verify
  actor eligibility and exact access first; preserve the local rule when the
  profile retains its semantics and no exact parent actor exists.
- Use protected credential delivery. Do not print, persist, request, or place
  credentials in repository files or commands.
- Prefer supported machine interfaces. Use the GitHub Web UI only for an exact
  control with no sufficient machine route, through an existing permitted session.
- Treat stale preview data, changed identity, target, visibility, parent state,
  product availability, or uncertain write result as a stop condition.

## Report

Report the bound identity and scopes, central authority decision, exact
before/desired/after values, parent attachments and effective state, operations,
paid or unavailable exceptions, ruleset migrations, repository residuals, and
repository-owned ruleset count for every in-scope repository. Do not claim effective
compliance from a successful request alone.
