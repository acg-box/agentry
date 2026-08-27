---
name: macos
description: Manage Developer ID-notarized Sparkle macOS ZIP releases only when the repository's canonical GitHub owner is acg-box. Use when Codex must audit, migrate, normalize, operate one authorized stable release, reconcile a failed run, or verify published bytes. For repositories outside acg-box, stop as not applicable without adoption guidance, file changes, release work, or ACG Box topology. Do not use for DMG, PKG, or non-Sparkle workflows.
---

# Manage ACG Box macOS Releases

## Enforce The Organization Gate First

Before any release audit or mutation, resolve the target repository's canonical
GitHub owner through its authoritative remote and provider metadata. Continue only
when that owner is `acg-box`. A directory name, fork name, user statement about
similar policy, or copied workflow does not replace this check.

If the canonical owner is outside `acg-box`, stop as **not applicable**. Do not
audit the repository toward adoption, propose ACG Box normalization, change files,
operate or verify a release under this standard, or inspect or apply the ACG Box
secret and signing topology. If ownership cannot be resolved, stop with an
applicability gap instead of assuming access.

This plugin owns ACG Box organization release standards. Its only current skill is
this macOS Sparkle ZIP skill. Add a separate skill only after a real release type
has evidence and an independent owner contract. Do not create empty future skills
or a generic root standard. The public invocation is
`$acg-release:macos`.

## Confirm Scope And Authority

After the organization gate passes, apply this skill only to an ACG Box macOS
application that distributes one regular Sparkle-enabled app bundle in a ZIP
through GitHub Releases. A DMG, PKG, bare app, non-Sparkle updater, Mac App Store
release, or other distribution lane needs a different owner. Report the scope
mismatch without adapting this standard to it.

Only after the organization and distribution-scope gates pass, read [the canonical
standard](references/standard.md) completely before an audit, migration,
normalization, release operation, recovery, or verification. The target
repository's instructions, source, tests, workflows, runbooks, current provider
documentation, and observed GitHub and Apple state remain authoritative.

Default to a read-only audit when the requested mode or mutation authority is not
clear.

- **Audit:** inspect repository and live metadata without changing either.
- **Migrate or normalize:** change only the authorized repository. This mode does
  not authorize certificate or secret changes, provider settings, tags, workflow
  approvals, Releases, notarization submissions, or app installation.
- **Operate:** bind the exact repository, version, commit, target adapter, and
  permitted release mutations. A clear request to publish one named version can
  authorize its tag push and workflow follow-through. It does not authorize
  certificate or Sparkle-key rotation, secret mutation, environment-rule changes,
  tag movement, manual publication, release deletion, or local installation.
- **Verify or reconcile:** keep reads and bounded recovery inside the existing
  release contract. Treat a new tag, new notarization submission, public-state
  mutation, or destructive draft repair as a separate operation unless the current
  authority clearly covers it.

Keep these boundaries separate: repository writes, tag creation and push,
protected-environment approval, public Release mutation, installation, certificate
creation or rotation, Sparkle-key rotation, and secret mutation. Authority for one
boundary does not authorize another.

## Enforce Developer ID Distribution

The production policy is Developer ID Application signing with Hardened Runtime,
secure timestamps, Apple notarization, stapling, strict signature verification, and
Gatekeeper assessment. An Apple Development, Personal Team, ad hoc, timestamp-free,
unnotarized, or Open Anyway path is legacy drift to migrate. Never operate or
publish that path as an ACG Box production release.

Do not invent an Apple Team ID, certificate suffix, signing identity, entitlement,
or product identity. Read these values from the target repository's adapter and
confirm them against the imported identity and signed code. Xcode account presence
alone does not prove that a usable Developer ID identity or notary credential exists.

## Work

1. Inventory the source validator, release workflow, native tests and build,
   signing and packaging adapters, notarization flow, publisher, contract tests,
   runbook, version owners, Sparkle pin, checked-in public key, effective secret
   access, protected environment, tags, Releases, and relevant run evidence.
2. Bind every repository-owned adapter value. Keep app names, bundle identifiers,
   Apple Team ID and identity selector, asset names, feed URLs, Sparkle versions and
   revisions, entitlements, and public keys in the target repository.
3. Compare the evidence with the complete standard. Report exact drift, scope
   mismatch, unavailable live evidence, and exceptions before mutation. A legacy
   Apple Development workflow requires migration; it is not an alternate policy.
4. For migration or normalization, implement the smallest repository-owned adapter
   and behavior tests. GitHub Actions must run from checked-in source and must never
   depend on an installed Codex plugin.
5. For operation, complete credential-free validation before the authorized tag
   leaves the machine. Confirm live certificate and notary readiness before the
   workflow reaches privileged work. Push no tag until the named source passes and
   release-trigger authority is explicit. Monitor only that workflow to a terminal
   state.
6. Preserve the required artifact order: sign inside-out, verify, make a separate
   notarization upload ZIP, obtain and read back an `Accepted` notarization result
   and log, staple and validate the app, create the final public ZIP, then create
   the Sparkle signature, appcast, and checksum from that final ZIP.
7. After publication, download the public assets and verify remote bytes, metadata,
   checksum, appcast, Sparkle signature, notarization ticket, complete code-signing
   graph, Gatekeeper acceptance, and version. Workflow success alone is not release
   acceptance.
8. On failure, use the standard's bounded reconciliation rules. Never move a remote
   tag, bypass notarization or environment approval, publish a draft manually, hide
   uncertainty with unbounded retries, or rebuild bytes behind an existing signature.

## Hard Boundaries

- Never print, request in chat, copy into source, or persist secret values. Inspect
  only secret names, scopes, effective access, and shadowing risk.
- Never create, revoke, renew, export, or rotate an Apple certificate or Sparkle
  key without exact authority. Never rotate both trust roots in one update.
- Never infer live-release authority from repository-write authority, a passing
  check, a local build, an installed account, or an installed app.
- Never weaken signing, timestamp, notarization, stapling, signature, or Gatekeeper
  gates to make a release continue.
- Never require a target workflow to call this skill or any plugin runtime.
- Never convert an uncertain GitHub or Apple mutation into success without
  authoritative readback of the exact intended state.

## Report

Report the canonical owner result, mode, scope result, authority used, current and
desired contract, repository adapters preserved, exact mutations, validation
evidence, release and public-asset evidence, and honest live-readiness gaps.
Distinguish checked-in validation from a successful notarized release under the
same exact pipeline.
