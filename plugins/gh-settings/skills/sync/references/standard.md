# GitHub Governance Standard

## Scope And Authority

Audit or reconcile the requested profile against the exact authorized GitHub
host, accounts, repositories, and mutation scopes. Use the complete in-scope
repository inventory, including private, archived, and template
repositories. Establish identity, permissions, plan, and billing where they
affect the requested controls.

Organization-wide work uses supported organization enforcement and defaults, then
repository settings, within the authorized scope.
Repository-scoped work keeps parent state read-only while accounting for inherited
controls. Neither mode grants authority to modify a higher scope.

A parent default is not enforcement. Preserve documented override precedence and
avoid duplicate lower-scope settings when an enforced parent provides the desired
outcome. Remove an equivalent lower-scope override only after effective inheritance
from its replacement is verified.

Use the environment's protected credential route and supported machine interfaces.
Use an existing permitted browser session only for an exact control without a
sufficient machine route. A new login needs user authority. Check current official
GitHub documentation for API support, product availability, and billing.

## Security Profiles

For a maximum-free public baseline, include Code Security and CodeQL, Secret
Protection and push protection, dependency graph, Dependabot alerts and security
updates, private vulnerability reporting, and applicable free dependent features.
Verify configuration fields, enforcement, defaults, and actual repository
attachments. An unattached configuration does not establish effective settings.

Preserve active advanced CodeQL setup or select the supported advanced-setup
allowance when attaching a parent configuration. Do not remove working advanced
setup merely to make the attachment succeed.

For a free private baseline, enable only features supported without
charge by the current plan, including dependency graph and Dependabot alerts and
security updates. Disable Code Security, Secret Protection, CodeQL, secret scanning,
push protection, and paid dependent features unless separately authorized. Keep
malware alerts within their supported ecosystems and delegated dismissal disabled
when it requires a paid product.

Code Quality is separate from CodeQL and Code Security. For a no-extra-cost
profile, keep it disabled on public and private repositories. Where organization
controls are available, require `No repositories`
with `Enforce access`; the default alone does not disable repository opt-ins.
Read back effective repository analysis as off. Never enable the product to expose
a hidden control or complete verification.

### Prevent Additional Charges

Preserve the authorized subscription. Do not enable additional paid products or
metered charges without user authority. Keep confirmed free features. Trials,
discounts, included quotas, and public visibility do not prove that a feature and its
dependent Actions, storage, or AI workloads cannot incur charges.

Within the authorized scope, disable unapproved paid products and use parent
enforcement to prevent lower scopes from enabling them again. For retained metered
services, verify a supported zero-paid-spend stop while preserving included free
usage where supported. Report an uncovered cost risk instead of enabling a feature
with uncertain billing to maximize security coverage.

Budgets supplement product controls. Verify current product/SKU support, units,
scope, exclusions, and stop-usage enforcement. Alert-only budgets do not cap use.
Do not assume Code Quality supports a budget or that a GHAS budget disables
existing paid enablement. Recheck
provider capabilities instead of treating historical API limitations as permanent.

For account-wide cost audits, inspect billable usage. Cost control does not
authorize removing people or repository access.

Verify effective product state, restrictions on re-enablement, and current-period
net charges separately. Account for reporting delay and usage before a budget
existed or a product was disabled. Report remaining
charges and gaps; do not promise a monthly total or zero future charges from
current settings, absent usage records, or partial-period totals alone.

### Automatic Dependency Submission

Treat automatic dependency submission as a separate Actions workload with its own
dependency-graph, Actions, ecosystem, runner, and billing prerequisites. It is not
controlled by the Dependabot runner setting.

For a maximum-free public baseline, enable it with the standard runner after
confirming current free usage. For private repositories, leave it
disabled unless the user accepts Actions usage and possible charges. Prefer free
Dependabot graph jobs where they take precedence. Report enablement with no current
effect when the repository has no supported manifest.

### Dependabot Defaults

Prefer organization defaults for grouped security updates. Preserve precedence:
`dependabot.yml` group rules, then repository UI, then organization UI. Grouping
requires dependency graph, alerts, and security updates, and can replace existing
pull requests.

Use standard GitHub runners; public repositories use GitHub-hosted runners. Select
a labeled runner only when an exact eligible available runner exists. A settings
request does not require creating runner infrastructure.

## Rulesets And Protection

Inspect effective parent and repository rulesets separately, plus branch
protection that affects the requested outcome. Preserve retained rules and bypass
semantics when moving ownership.

For a zero-repository-ruleset profile, distinguish two decisions for each local ID:

- **Migrate:** The profile retains its semantics. Create and verify equivalent
  parent target, ref, rule, actor, and enforcement coverage before local deletion.
- **Retire:** The user accepts removal and the disclosed protection delta. Verify
  the accepted parent baseline and delete that exact local ID. Do not invent a
  team, role, app, or adapter to preserve semantics the profile retires.

A user-specific bypass may have no exact parent actor. Verify eligibility and
access before proposing a replacement; secret teams are not eligible. If retained
semantics have no equivalent parent actor, preserve the local rule and report the
gap unless the user changes the profile. Changes to identity containers need exact
authority.

Before activating parent pull-request rules, every target repository must retain
an allowed merge path. Do not weaken inherited protection or widen bypass access
outside the approved change.

### Merge-Commit-Only Profile

Use these repository values:

- `allow_merge_commit: true`;
- `allow_squash_merge: false`; and
- `allow_rebase_merge: false`.

Where supported, enforce `allowed_merge_methods: ["merge"]` in the parent
pull-request rule as well; it does not set the repository toggles. Resolve any
effective `required_linear_history` conflict before activation, with authority for
the exact conflicting object. Preserve merge-title and message defaults unless
the profile changes them.

## Other Settings

Apply central ownership to release immutability, web commit signoff, Projects,
Actions, and product policies where the current GitHub interface supports the
requested outcome. Commit comments can be a parent default with repository
overrides. Do not expand a settings request to unrelated Actions policies.

Repository residuals include features such as Issues, Wikis, Discussions,
Sponsorships, pull-request availability and creation policy, merge options,
branch-update suggestions, auto-merge, head-branch deletion, and linked-issue
closure. Inspect the residuals requested by the profile.

A visibility-dependent feature does not authorize changing visibility or adding a
funding file. If a prerequisite exposes a previously unavailable control, make the
dependent change conditional on its newly observed state.

## Preview And Reconciliation

Before live writes, show the exact targets, current and desired values, material
parent effects, planned interface, charges, and destructive object IDs. Identify
unknown or conditional changes. For automatic dependency submission, disclose its
own prerequisites and billing effect. Choose a presentation proportionate to the
requested scope.

Existing user authority can cover the previewed changes. Request more authority
only for additional targets, scopes, products, charges, destructive objects, or
values outside that authority.

Refresh material state before applying drift. Create and verify replacement parent
controls before deleting retained local protection, and establish allowed merge
methods before activating dependent parent rules. Resolve uncertain mutation
results from authoritative state before further writes to the affected target.
Show a corrected preview when material state changes; resume within existing
authority once the state is clear. Unresolved state leaves affected writes suspended.

Verify changed controls and effective repository state after parent changes.
Security attachments must reach a successful terminal state; a failed or pending
attachment is not acceptance. Do not enable a paid product to force attachment.

## Completion

Report material changes, effective remaining drift, and unavailable or paid
exceptions with enough evidence to assess the requested profile. Include exact
ruleset migration or deletion results; a zero-local-ruleset profile requires a
verified count of zero for every target repository.

Claim reconciliation only when applicable desired values have authoritative
readback and no unresolved write remains. Otherwise state the remaining gap.

## Provider References

Use current official documentation for the controls involved:

- [Organizations](https://docs.github.com/en/rest/orgs/orgs) and
  [repositories](https://docs.github.com/en/rest/repos/repos);
- [rulesets](https://docs.github.com/en/rest/repos/rules);
- [security configurations](https://docs.github.com/en/rest/code-security/configurations);
- [Actions permissions](https://docs.github.com/en/rest/actions/permissions); and
- [GraphQL](https://docs.github.com/en/graphql/reference).

For cost controls, consult [budgets and alerts](https://docs.github.com/en/billing/concepts/budgets-and-alerts),
and [Code Quality disablement](https://docs.github.com/en/code-security/how-tos/maintain-quality-code/disable-code-quality).

Consult the relevant product documentation for billing, default precedence,
attachment compatibility, and automatic dependency submission prerequisites.
