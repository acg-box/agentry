# GitHub Governance Standard

## Purpose

Use this standard to audit and reconcile GitHub Enterprise, organization, and
repository controls. Default to a read-only audit. Reconcile only the exact
targets, scopes, products, and values that the user authorizes.

Use central-first authority. Put a control at the highest GitHub scope that can
manage the required outcome. Use repository settings only for controls that
GitHub cannot manage at Enterprise or organization scope, or for an explicit
repository exception that the parent policy permits.

GitHub changes its APIs, plans, billing rules, and Web UI. Before each live
operation, use the current-documentation route and official GitHub documentation.
Bind the supported API version. Do not use examples in this standard as proof of
current availability.

## Authority And Target Binding

Resolve these facts before privileged collection:

- GitHub host, API base URL, and selected API version;
- authenticated login, stable user ID, credential-delivery route, and effective
  administration scopes;
- exact Enterprise slug and stable identity, when in scope;
- exact organization login, ID, node ID, plan, and billing boundary;
- the complete in-scope repository inventory, including IDs, node IDs,
  visibility, archived state, template state, and permissions;
- requested profile and whether the request is audit-only or authorizes writes;
- allowed mutation scopes: Enterprise, organization, and repository; and
- observation time.

A repository-scoped request does not authorize an organization or Enterprise
change. An organization-scoped request does not authorize an Enterprise change.
A profile is desired state. It is not proof that the current plan, product, or
parent policy permits that state.

Use a protected credential adapter, connector, or supported CLI authentication
route declared by the active environment. Deliver a credential only to the named
GitHub consumer. Never show token values, inspect unrelated credential stores, or
fall across identities after an authorization failure.

## Operating Modes

Select one mode from the user's authorized scope before classification.

### Organization-Wide Mode

Use central-first authority across the complete Enterprise, organization, and
repository inventory. Put every supported control at Enterprise or organization
scope. Reconcile only true repository residuals. When the approved profile requires
zero repository-owned rulesets, treat a nonzero local count on any repository as
failed acceptance.

### Repository-Scoped Mode

Bind one exact repository and keep all Enterprise and organization state read-only.
Audit inherited rulesets, configurations, policies, and defaults so effective state
is correct, but do not mutate a parent. Reconcile only the repository values that
the request authorizes. Do not infer organization-wide authority from a repository
profile or from this standard's central-first default.

## Central-First Decision Rule

Classify each requested control before previewing a write.

| Class | Meaning | Action |
| --- | --- | --- |
| Enterprise-enforceable | GitHub can enforce the outcome across the required Enterprise scope. | Own the control at Enterprise scope. |
| Organization-enforceable | GitHub cannot provide the required Enterprise control, but the organization can enforce it. | Own the control at organization scope. |
| Central default | GitHub can set a parent default, but a repository can override it. | Set the parent default and report override precedence. |
| Repository-only | GitHub has no sufficient Enterprise or organization control for the required outcome. | Reconcile each applicable repository. |
| Paid or unavailable | The active plan, product, interface, or prerequisite cannot provide the approved outcome safely. | Do not enable or emulate it. Report the gap. |

Use the highest scope only when it provides equivalent or stronger semantics for
the requested target set. Do not replace an enforcement rule with a default. Do
not describe a default as effective enforcement. Do not write duplicate
repository settings when an enforced parent value already supplies the outcome.

When a parent default is repository-overridable, audit the parent value and each
material repository override separately. Preserve documented precedence, such as
`dependabot.yml` over repository UI and repository UI over organization UI.

When an organization setting overrides an equivalent Enterprise default, remove
the duplicate organization override only after the Enterprise default is active
and effective readback proves that the organization still inherits the intended
value.

## Interface Selection

Prefer the smallest supported interface that can read and write the same control:

1. a purpose-built GitHub connector or supported API;
2. GitHub CLI as an authenticated API client;
3. the GitHub Web UI for one exact setting that has no sufficient supported
   machine interface.

Do not use the Web UI only because GitHub describes a control with a UI label.
First check current REST and GraphQL documentation. If a public interface exposes
read state but not mutation, use the UI only for the missing operation and verify
through both available surfaces when possible.

For UI fallback, preserve the bound host, identity, account, repository, and
control. Use the existing signed-in session. If the session needs a new login or
credential entry, stop unless the user explicitly authorizes that login. Never
handle the credential value. Read the visible control, change only the previewed
value, submit, reload, and read it again. Record an inaccessible control as a gap.

## Audit Inventory

Collect the requested controls and the parent state that can determine their
effective values. Inventory every in-scope repository. Do not omit private,
internal, archived, or template repositories.

### Security Configurations And Products

List Enterprise and organization security configurations, their defaults, full
fields, enforcement, and attached repositories. For each repository, read the
attached configuration endpoint. A catalog entry without an attachment is not
effective state. Distinguish `attached`, `enforced`, `removed`, `failed`, and
transitional statuses.

For a public baseline, audit these fields:

- Code Security, CodeQL default setup, runner type, and advanced-setup
  compatibility;
- Secret Protection, secret scanning, validity checks, extended metadata,
  generic and AI detections, push protection, and bypass policy;
- dependency graph, automatic dependency submission, Dependabot alerts,
  security updates, malware alerts, and delegated dismissal;
- private vulnerability reporting; and
- configuration enforcement and default repository visibility.

For a maximum-free public baseline, enable automatic dependency submission with
the standard runner after GitHub Actions and current billing evidence are bound.
Report when the attached configuration is effective but no current supported
manifest can trigger a submission.

Code Security and Secret Protection are free for public repositories. CodeQL
default setup cannot attach over active advanced setup unless the configuration
allows advanced setup. Preserve active advanced setup or use the explicit
"advanced setup allowed" option. Do not remove a working advanced setup only to
make a parent attachment succeed.

For a free private or internal baseline, enable only features that current plan
evidence proves are free for that visibility. Dependency graph, Dependabot alerts,
and Dependabot security updates are available on all plans. Malware alerts require
Dependabot alerts and currently cover only supported ecosystems. Explicitly
disable automatic dependency submission unless the user accepts its GitHub Actions
usage and possible private-repository billing. Also disable Code Security, Secret
Protection, CodeQL, secret scanning, push protection, and their paid dependent
features. Keep delegated dismissal disabled when the current product requires Code
Security.

Treat automatic dependency submission as a separate Actions workload, not as part
of the Dependabot runner setting. It requires dependency graph and GitHub Actions,
runs built-in workflows on supported manifests, and consumes Actions minutes.
Standard GitHub-hosted runners are free for public repositories; private and
internal repositories can consume included minutes and incur charges beyond the
allowance. Inspect current manifest ecosystems before enablement. Prefer the
no-charge Dependabot graph jobs where GitHub supports them because they take
precedence over automatic submission. Use the standard runner option unless an
exact eligible labeled runner is already available. Report when enablement has no
current effect because no supported manifest exists, and still read back the
configuration field and every attachment.

Treat GitHub Code Quality as a separate product. Audit its Enterprise allowance,
organization repository access, enforcement, and repository state. Do not infer
authority from CodeQL or Code Security. Never enable Code Quality where the
approved result is `No repositories`. If GitHub cannot set and enforce that state
without starting scans or charges, leave the product disabled and report the gap.

### Dependabot Global Controls

Audit grouped security updates, malware alerts, delegated dismissal, and the
Dependabot runner type. Grouped updates require dependency graph, Dependabot
alerts, and Dependabot security updates. Enabling grouping can close and replace
existing pull requests.

Prefer the organization default for grouping. Preserve current precedence:

1. `dependabot.yml` group rules;
2. repository UI; and
3. organization UI.

Use the standard GitHub runner by default. Inspect organization and Enterprise
runner inventories before selecting a labeled runner. Do not select a labeled or
self-hosted runner unless an eligible, available runner with the exact label
exists. Public repositories use GitHub-hosted runners.

### Rulesets And Branch Protection

List Enterprise, organization, and repository rulesets with full details. For each
repository, list rulesets with parents included and excluded. Classify each rule by
ID, name, target, source type, source, enforcement, bypass actors, conditions, and
rules. Inspect branch protection when it can add or conflict with effective state.

For a profile that requires zero repository-owned rulesets, classify each local
rule as `migrate` or `retire` before deletion.

- `migrate`: The profile retains the rule's semantics. Create a parent replacement
  that preserves its exact target, ref pattern, rules, bypass actors, and
  enforcement. Read back effective coverage before local deletion.
- `retire`: The user explicitly accepts removal and the disclosed protection delta.
  Refresh sufficient parent protection, then delete only the exact local IDs from
  the preview. Do not create a team, role, app, or other preservation adapter for
  semantics that the approved profile says to remove.

Never delete first, silently weaken retained protection, or widen bypass access.

A user-specific repository bypass might not have an exact parent-scope actor.
Check current supported bypass types, source ownership, team visibility, membership,
and repository access before proposing a team or role. Secret teams are not eligible
for ruleset bypass. Do not create or alter an identity container without an exact
preview. When no exact central actor preserves retained semantics, keep the
repository rule and report the centralization gap unless the user explicitly
changes the profile to retire that rule.

For pull-request rules, confirm that every target repository has at least one merge
method allowed by the parent rule before activation. Preserve existing lifecycle,
signature, deletion, non-fast-forward, workflow, and required-check rules unless
the user explicitly changes them.

### Organization Defaults And Policies

Audit current central controls for:

- immutable releases;
- required signoff for web commits;
- commit-comments default and repository override behavior;
- organization and repository Projects availability;
- Actions repository access, allowed actions, SHA pinning, workflow-token
  permissions, pull-request approval, and runner inventory; and
- security product access and enforcement.

Release immutability is an organization policy when GitHub exposes that control.
Use repository release settings only when the requested target is outside the
central policy or GitHub does not expose the parent control. Web commit signoff is
an organization control. Commit comments are an organization default that
repository administrators can override.

Do not change unrelated Actions policies during a settings profile reconciliation.
Preserve an existing safe setting unless the approved profile names another value.

### Repository Residuals

After central classification, audit only true residuals and allowed exceptions.
Typical residuals include:

- Issues, Wikis, Discussions, Sponsorships, and Pull Requests;
- issue and pull-request creation policy;
- allowed merge methods and their unchanged title or message defaults;
- branch update suggestions, auto-merge, and head-branch deletion;
- commit comments when a repository override must be reconciled; and
- automatic closing of linked issues after merge.

### Merge-Commit-Only Baseline

When the approved profile selects merge-commit-only behavior, use these exact
repository values:

- `allow_merge_commit: true`;
- `allow_squash_merge: false`; and
- `allow_rebase_merge: false`.

Repository merge toggles remain repository residuals because an account ruleset
does not set those repository values. When a parent pull-request rule supports
allowed merge methods, use `allowed_merge_methods: ["merge"]` to enforce the same
outcome on its matched refs.

Before activation, inspect every effective Enterprise, organization, repository,
and branch-protection rule for `required_linear_history` or another condition that
rejects merge commits. Do not leave an active conflict. Change or remove a
conflicting rule only when the approved preview names that exact parent object.
Preserve merge-title and merge-message defaults unless the profile names them.

Apply visibility and feature prerequisites literally. `Sponsorships enabled for
public repositories` does not authorize a visibility change or a funding file.
If a control appears only after its prerequisite is enabled, classify the initial
state as unknown and make the dependent write conditional on fresh readback.

## Exact Drift Preview

Show the preview before the first live write. Bind it to the host, identity,
Enterprise, organization, complete repository inventory, API version, observation
time, selected operating mode, allowed mutation scopes, current parent state, and
user authority.

Separate the preview into:

1. Enterprise-enforceable changes;
2. organization-enforceable changes;
3. central defaults and repository override precedence;
4. repository-only residuals;
5. paid, unavailable, skipped, and unknown controls; and
6. destructive migrations.

For a zero-repository-ruleset profile, list every local ruleset and mark it
`migrate` or `retire`. State the required acceptance value: local ruleset count
`0` for every repository.

Use one row per control with these columns:

| Scope | Control | Current | Desired | Authority/source | Planned interface | Status |
| --- | --- | --- | --- | --- | --- | --- |

Use precise statuses such as `in sync`, `change`, `conditional change`,
`parent-controlled`, `central default`, `repository override`, `paid opt-in
required`, `unsupported`, and `unknown`.

After the table, list operations in order. For REST, show method, path, and only
changed fields. For GraphQL, show the mutation, stable node ID, and changed inputs.
For UI, show the exact page and control. For deletion, show the exact object ID,
source, target, rules, and replacement.

Give automatic dependency submission its own preview row with dependency-graph and
Actions prerequisites, supported-ecosystem evidence, runner choice, and the public
or private Actions billing result. Do not hide it inside the dependency-graph or
Dependabot-runner rows.

The same user request can supply mutation authority when it binds the exact
accounts, repositories, profile, and scopes. The preview is still mandatory. Stop
for new authority if the preview adds a target, scope, product, charge, destructive
object, or value that the request did not bind.

## Reconciliation

Refresh every previewed value immediately before writing. Recompute drift. A
changed identity, target, visibility, parent control, product availability,
destructive object, or uncertain result invalidates the preview.

Apply the smallest sufficient writes. Use this order unless a dependency requires
a safer sequence:

1. create or update non-destructive parent controls;
2. set and verify parent defaults, then remove duplicate lower-scope defaults;
3. prepare repository residuals that a new parent rule requires, such as an
   allowed merge path;
4. attach enforced security configurations and wait for terminal status;
5. activate parent rulesets;
6. verify effective parent coverage; and
7. delete only exact migrated or explicitly retired repository-owned rules.

Send only changed fields. Keep unrelated merge-title and message defaults. Separate
API families when their result or rollback boundary differs. Do not treat an
omitted response field as success. After an uncertain timeout or partial response,
stop writes to that target until authoritative readback resolves the result.

For an asynchronous attachment, poll the authoritative status with bounded waits.
Do not report success while the status is `attaching`, `updating`, `failed`,
`removed`, or absent. Diagnose a failed attachment before retrying. Do not consume a
paid license to force attachment.

## Readback And Result

Read each changed control from its authoritative interface. Re-list parent and
repository-only rulesets. Re-read security configuration defaults, fields,
repository attachments, and effective security state. Reload each UI-only page.
Re-audit every repository after parent changes so local state and inherited state
remain distinct.

Report:

- bound target, identity, plan, API version, and observation time;
- Enterprise and organization controls and which values are enforced;
- central defaults and documented repository override precedence;
- each repository's attached configuration status and effective fields;
- before, desired, and read-back values for each changed control;
- exact operations and outcomes;
- migrated and deleted ruleset IDs with replacement evidence;
- repository-owned ruleset count for every repository and the profile acceptance
  result;
- paid-product gates, conditional skips, unsupported controls, and failures; and
- remaining effective drift.

Use `reconciled` only when every applicable desired value has authoritative
readback and no unresolved write remains. Otherwise use `partially reconciled` or
`audit complete` and state the exact gap.

## Official Documentation Anchors

Check current official versions of these sources before live work:

- REST organizations: `https://docs.github.com/en/rest/orgs/orgs`
- REST repositories: `https://docs.github.com/en/rest/repos/repos`
- REST repository and account rulesets:
  `https://docs.github.com/en/rest/repos/rules`
- REST code security configurations:
  `https://docs.github.com/en/rest/code-security/configurations`
- REST Actions permissions:
  `https://docs.github.com/en/rest/actions/permissions`
- GraphQL organizations and repositories:
  `https://docs.github.com/en/graphql/reference`
- security configuration statuses and troubleshooting;
- public and private security-feature availability and billing;
- Dependabot security updates, grouping precedence, malware alerts, delegated
  dismissal, and runner selection;
- automatic dependency submission, supported ecosystems, runner selection, and
  GitHub Actions billing;
- immutable releases and organization repository defaults;
- organization commit-comments and web-signoff controls; and
- Code Quality enablement, enforcement, and billing.
