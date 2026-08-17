# GitHub Settings Standard

## Purpose

Use this standard to audit GitHub Web UI settings, show exact drift, and reconcile
only explicitly approved repository changes. The audit is read-only by default.

GitHub changes its APIs, plan boundaries, and Web UI. Before each live operation,
use the environment's current-documentation route and official GitHub documentation.
Bind the supported API version explicitly. Do not rely on examples in this standard
as proof of current availability.

## Authority And Target Binding

Resolve these facts before collecting privileged state:

- GitHub host and API base URL;
- authenticated login and credential delivery route;
- exact `owner/repository`, numeric repository ID, node ID, and visibility;
- repository permission held by the authenticated identity;
- requested profile and whether the request is audit-only or authorizes writes;
- allowed mutation scopes: repository, organization, and enterprise; and
- observation time and current API or documentation version.

A request to reconcile one repository does not authorize an organization or
enterprise change. A profile is desired state, not proof that the current plan or
parent policy permits it.

Use a protected credential adapter, connector, or supported CLI authentication
route declared by the active environment. Deliver the credential only to the named
GitHub consumer. Never show token values, inspect unrelated credential stores, or
fall across identities after an authorization failure.

## Interface Selection

Prefer the smallest supported interface that can read and write the same control:

1. a purpose-built GitHub connector or supported API;
2. GitHub CLI as an authenticated API client;
3. the GitHub Web UI for an exact setting that has no sufficient supported machine
   interface.

Do not use the Web UI only because a control is described by a UI label. First check
current REST and GraphQL documentation. If the public interfaces expose read state
but not mutation, use the UI only for the mutation and verify through both available
surfaces when possible.

For UI fallback, preserve the exact host, identity, owner, repository, and control.
Use the existing signed-in session. If the session needs a new login or credential
entry, stop unless the user explicitly authorizes that login; never handle the
credential value. Read the visible control, change only the previewed value, submit,
reload the page, and read it again. Record an unsupported or inaccessible control as
a gap instead of guessing.

## Audit Inventory

Collect only settings that the requested profile needs, plus parent controls that
can determine their effective state.

### Repository Features And Collaboration

Typical repository-owned controls include:

- Issues, Projects, Wikis, Discussions, Sponsorships, and Pull Requests;
- pull request creation policy;
- allowed merge methods and their title or message defaults;
- branch update suggestions, auto-merge, and head-branch deletion;
- web commit signoff;
- commit comments;
- automatic closing of issues from merged linked pull requests; and
- release immutability.

Current REST `PATCH /repos/{owner}/{repo}` and GraphQL `updateRepository` cover
different subsets. Query the repository through the corresponding read surface.
Repository release immutability has its own repository endpoint. Some newer Web UI
controls can have no supported public mutation field; classify them as UI-only after
checking current documentation.

Apply conditional profile clauses literally. For example, `Sponsorships enabled for
public repositories` means skip the control for a private repository; it does not
authorize a visibility change.

### Rulesets And Parent Controls

List repository rulesets twice:

- include parents to see every applicable repository, organization, and enterprise
  ruleset; and
- exclude parents to isolate repository-owned rulesets.

Classify each ruleset by ID, name, target, source type, source, enforcement, bypass
actors, conditions, and rules. Fetch full details before proposing a deletion.

An instruction such as `no repository-owned rulesets` authorizes no action against
an organization- or enterprise-owned ruleset. Delete only an exact ruleset whose
`source_type` and `source` identify the bound repository and whose ID and full detail
were present in the approved preview. Re-list both views after deletion.

Also inspect applicable branch protection when the requested profile or ruleset
audit depends on it. Do not treat a clean repository-only list as proof that the
repository has no effective protections.

### Security And Product Boundaries

Read repository visibility first. Then inspect:

- the repository `security_and_analysis` block when the identity can see it;
- dependency graph and Dependabot alert state;
- Dependabot security update state, including a paused result;
- grouped security updates;
- Dependabot malware alerts and their supported npm-only scope;
- Dependabot delegated alert dismissal (`Prevent direct alert dismissals`);
- Dependabot on Actions runners and the effective runner type/label;
- code scanning default setup and its language availability;
- secret scanning and push protection;
- the code security configuration attached to the repository, including its source
  and enforcement; and
- Code Quality setup only to confirm that it is not unintentionally selected.

### Free Dependabot Repository Baseline

When the requested profile selects the repository free baseline and current official
documentation confirms availability, audit these repository-owned controls together:

- dependency graph, Dependabot alerts, and Dependabot security updates;
- grouped security updates, which require the three preceding prerequisites and may
  reorganize existing Dependabot pull requests;
- Dependabot malware alerts, enabled only after Dependabot alerts and currently
  limited to the npm ecosystem; and
- `Prevent direct alert dismissals`, when the repository exposes the control without
  requiring a paid or otherwise unapproved prerequisite. When available, it makes
  users with repository write access submit dismissal requests while organization
  owners and security managers can approve or deny requests or dismiss alerts
  directly. Confirm that reviewers have enough coverage before enabling this
  workflow.

For Dependabot on Actions runners, select the standard GitHub-hosted runner by
default. Inspect repository and organization runner inventory and labels before
considering self-hosted execution. Do not select self-hosted mode unless an eligible,
available runner with the exact configured label exists; otherwise keep standard
GitHub runners so Dependabot jobs do not queue indefinitely.

Grouped updates, malware alerts, and standard Dependabot runners are separate from
Code Security, Secret Protection, and Code Quality. Delegated Dependabot dismissal
may require Code Security to be enabled for the repository in the current GitHub
UI. If the control reports that prerequisite, classify it as `paid opt-in required`
or `unsupported` under the active profile and leave it disabled; never enable Code
Security, Secret Protection, or Code Quality just to satisfy delegated dismissal.
The free baseline does not authorize any paid product or any organization or
enterprise mutation.

For a private or internal repository, enable only controls that current plan evidence
shows do not activate a paid add-on. Do not enable `advanced_security`, Code Security,
Secret Protection, CodeQL or code scanning, secret scanning, or push protection when
the operation would activate a paid product unless the user explicitly selects that
named product and accepts the billing scope. A pre-existing paid feature can be
audited without authority to change it.

GitHub Code Quality is not CodeQL and is not the code scanning baseline. It has its
own product, setup surface, license, and usage costs. Enable it only under separate,
explicit product and billing authority.

Treat an attached or enforced organization or enterprise security configuration as
parent authority. The repository's code-security-configuration readback is the
authoritative attachment check: only an attached or enforced configuration supplies
effective parent values for this repository. A configuration that merely exists in
the organization catalog, or is listed without an attachment to this repository,
is informational and must not be reported as effective state. Report attached
configuration values, and do not edit, detach, replace, or weaken them during
repository-only work. If an attached configuration prevents a requested repository
value, report the drift as parent-controlled rather than trying a broader mutation.

## Exact Drift Preview

Show the preview before the first write. Bind it to:

- GitHub host, authenticated login, exact `owner/repository`, repository ID, node ID,
  visibility, and observation time;
- allowed mutation scope and the user statement that grants or withholds it;
- current parent rulesets and security configuration;
- current documentation or API version; and
- every requested profile clause.

For the free Dependabot baseline, include one row for each of grouped security
updates, malware alerts, Prevent direct alert dismissals, and runner mode, plus
their dependency prerequisites and any attached configuration that can control them.

Use one row per control with these columns:

| Scope | Web UI label | Current | Desired | Authority/source | Planned interface | Status |
| --- | --- | --- | --- | --- | --- | --- |

Use precise statuses such as `in sync`, `change`, `conditional skip`,
`parent-controlled`, `paid opt-in required`, `unsupported`, and `unknown`.

After the table, list the exact operations in order. For an API call, show the HTTP
method, path, and only the fields that will change. For GraphQL, show the mutation
name, repository node ID, and changed inputs. For the Web UI, show the exact page and
control label. For a destructive action, show the exact object ID and full identity.

The same user request can supply mutation authority when it explicitly says to apply
or reconcile the exact repository and profile. The preview remains mandatory. Stop
for new authority if the preview adds a repository, scope, product, charge,
destructive object, or value that the request did not bind.

## Reconciliation

Refresh all previewed current values immediately before writing. Recompute drift. If
the target, visibility, identity, parent authority, requested product, or destructive
object changed, invalidate the preview and stop or show a new preview.

Apply the smallest sufficient mutations:

- send only changed fields in a repository update;
- keep unrelated merge title and message defaults unchanged unless the profile names
  them;
- separate API families when their result or rollback boundary differs;
- never interpret a defaulted or omitted response field as success;
- stop after an uncertain timeout or partial response until authoritative readback
  resolves the result; and
- do not broaden scope to make a rejected repository change succeed.

Order changes to preserve access and evidence. Apply non-destructive feature and
merge settings before destructive ruleset deletion. Enable a prerequisite before a
dependent free security feature. Do not disable a parent-enforced or pre-existing
security feature merely because it is absent from the requested profile. For the
free Dependabot baseline, verify dependency graph, alerts, and security updates
before grouped updates or malware alerts, and verify the effective alert-dismissal
reviewers before enabling delegated dismissal. Keep standard GitHub runners when no
matching self-hosted runner is available.

## Readback And Result

Read every changed value from the authoritative interface after mutation. Re-list
parent-inclusive and repository-only rulesets. Re-read the attached security
configuration. Reload and re-read each UI-only control. A successful request is not
enough.

Report:

- bound target, identity, visibility, and observation time;
- parent rulesets and security configuration left unchanged;
- whether any organization or enterprise configuration is attached/enforced for
  the repository, and which values are therefore effective;
- before, desired, and read-back values for each control;
- exact operations attempted and their outcomes;
- conditional skips, paid-product gates, inaccessible controls, and unsupported
  fields; and
- any effective drift that remains.

Use `reconciled` only when each applicable desired value has authoritative readback
and no unresolved write remains. Otherwise report `partially reconciled` or
`audit complete` with the exact gap.

## Official Documentation Anchors

Check the current versions of these GitHub sources before live work:

- REST repositories: `https://docs.github.com/en/rest/repos/repos`
- REST repository rules: `https://docs.github.com/en/rest/repos/rules`
- REST code security configurations:
  `https://docs.github.com/en/rest/code-security/configurations`
- Dependabot security updates and grouping:
  `https://docs.github.com/en/enterprise-cloud@latest/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-security-updates`
- Dependabot malware alerts:
  `https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-malware-alerts`
- Dependabot delegated alert dismissal:
  `https://docs.github.com/en/code-security/how-tos/manage-security-alerts/manage-dependabot-alerts/enable-delegated-alert-dismissal`
- Dependabot GitHub-hosted runners:
  `https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/configure-on-github-hosted-runners`
- REST code scanning: `https://docs.github.com/en/rest/code-scanning/code-scanning`
- GraphQL repository schema:
  `https://docs.github.com/en/graphql/reference/repos`
- GitHub Advanced Security billing:
  `https://docs.github.com/en/billing/concepts/product-billing/github-advanced-security`
- GitHub Code Quality billing:
  `https://docs.github.com/en/billing/concepts/product-billing/github-code-quality`
