---
name: sync
description: Use when auditing or reconciling GitHub Enterprise, organization, and repository governance against an authorized settings profile, with central-first organization controls and repository-scoped changes.
---

# GitHub Governance

Use the [governance standard](references/standard.md) for team policy. Read the
scope and authority sections plus the controls needed for the requested profile;
read the full standard for a comprehensive governance audit. Check current
GitHub documentation for control availability and billing.

For free-feature or cost-control requests, also read the standard's
`Prevent Additional Charges` section. Preventing unapproved charges is an
acceptance condition, not a conclusion from feature toggles alone.

Organization-wide work puts controls at the highest sufficient authorized scope.
Repository-scoped work keeps parent state read-only. Preserve the distinction
between enforced parent policy and repository-overridable defaults.

Default to a read-only audit unless the request authorizes reconciliation. Show
exact drift before live writes; existing authority remains valid for that drift.
Ask for additional authority only when the proposed change exceeds it, including
new paid products, charges, scopes, or destructive changes.

Verify effective settings after changes. Report the result, material drift and
exceptions, and evidence needed to assess completion.
