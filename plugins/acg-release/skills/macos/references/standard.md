# ACG Box macOS Sparkle ZIP Release Standard

## Purpose, Scope, And Authority

This is the current macOS skill standard for the ACG Box organization release
plugin. Use it only for repositories whose canonical GitHub owner is `acg-box` and
for macOS applications that publish one regular, Sparkle-enabled app bundle as a
ZIP through GitHub Releases. It defines the shared trust and publication contract.
Each target repository owns its executable adapter and product identity.

## Organization Applicability Gate

Resolve the exact target repository and its canonical GitHub owner before any
release audit or mutation. Bind the canonical remote to GitHub provider metadata.
Continue only when the canonical owner is `acg-box`.

For any repository outside `acg-box/*`, stop as **not applicable**. Do not audit it
toward this standard, propose adoption, change its files, operate or verify a
release under this contract, or inspect or apply the ACG Box certificate, notary,
Sparkle-key, secret, environment, or publisher topology. If the canonical owner
cannot be resolved, preserve the gap and stop before release work.

Repository-write or release authority does not override this organization gate.
Changing a remote or transferring a repository is a separate operation and cannot
be used as an implicit path into applicability.

This standard does not operate DMG, PKG, Mac App Store, bare-app, non-Sparkle, or
multi-product distribution lanes. Do not widen the skill to those formats during an
audit or release. Route them to a separate owner.

Provider behavior can change. Before a live operation, check current official
Apple, Sparkle, GitHub, and tool documentation for every material API,
runner, signing, notarization, update, or publication rule. Current user direction,
target source, and observed provider state override old examples and prior release
conclusions.

## Universal Release Invariants

Every supported production release must satisfy all of these invariants:

- one immutable annotated stable tag binds one reachable commit and version;
- credential-free validation and build finish before private material is written;
- every executable component is signed inside-out with a valid Developer ID
  Application identity, Hardened Runtime, and a secure timestamp;
- strict code-signing verification passes before notarization;
- Apple returns an `Accepted` notarization result that is read back with its log;
- the app receives and validates a stapled ticket;
- Gatekeeper accepts the stapled app;
- the public ZIP is created only after stapling and is different from the temporary
  notarization upload archive;
- the Sparkle signature, appcast length, and checksum bind the exact final ZIP;
- a secret-free protected publisher creates or repairs one private draft before one
  final publication mutation; and
- final acceptance uses downloaded public bytes, not workflow success alone.

An Apple Development, Personal Team, ad hoc, timestamp-free, unnotarized, or
**Open Anyway** distribution path is production drift. Audit it and plan its
migration. Never treat it as a supported alternate ACG Box release policy.

## Target Repository Adapter

Keep product and team identity in the target repository. Do not put these values in
this plugin:

- repository owner, slug, canonical remote, and default branch;
- app name, bundle name, bundle identifier, deployment minimum, and architecture;
- version files, workspace package inventory, and build-number policy;
- release ZIP, appcast, checksum, feed, and download names or URLs;
- exact Sparkle source, version, revision, framework graph, and checked-in public
  Ed25519 key;
- native test and build commands, app entitlements, and smoke-test scope;
- paid Apple Developer Team ID and the expected Developer ID Application identity
  selector;
- Xcode and Swift selection rules; and
- protected-environment reviewer and tag policy.

The target adapter must make each value observable and testable. Do not infer a
paid Team ID from an Apple Development certificate, an Xcode account, a display
name, a certificate-label suffix, or an earlier Personal Team workflow. Until ACG
Box publishes a stable organization-wide public selector, each target adapter owns
the exact Team ID and identity binding.

The target repository must contain every workflow, script, test, and runbook that
GitHub Actions needs. A locally installed Codex plugin is never a workflow
dependency.

Preserve the target repository's established implementation languages and owners.
Keep Shell thin around native macOS commands, strict error handling, traps, and
cleanup. Put GitHub API, JSON, SemVer, pagination, and publisher-state logic in a
repository-owned testable program instead of Shell. Do not migrate a stable binary,
plist, ZIP, or cryptographic validator only for language uniformity.

## Authorization And Lifecycle Boundaries

Treat each boundary independently:

| Boundary | Effect | Required authority |
| --- | --- | --- |
| Audit and validation | Reads source, metadata, credentials metadata, or artifacts and runs checks | Read authority |
| Migration or normalization | Changes target repository files | Repository-write authority |
| Release trigger | Creates and pushes one exact annotated tag | Explicit release and Git authority |
| Notarization submission | Sends one signed candidate to Apple | Exact live-release authority and usable notary credentials |
| Deployment approval | Allows the protected `release` environment job to continue | Exact environment approval authority |
| Publication | Changes a private draft into a public GitHub Release | Explicit publication authority carried by the approved workflow |
| Installation or rollout | Installs or activates the app for a user | Separate deployment or installation authority |
| Certificate lifecycle | Creates, exports, renews, revokes, or rotates Developer ID material | Exact Apple certificate authority |
| Sparkle-key lifecycle | Generates, imports, backs up, recovers, or rotates an application key | Exact application trust-root authority |
| Secret lifecycle | Creates, changes, scopes, or deletes a GitHub secret | Exact secret and provider authority |

A passing test, merged change, local account, installed certificate, local build,
tag, notarization submission, environment approval, public Release, and installed
app are different facts. Never use one as proof or authorization for another.

## Immutable Source Contract

Use one stable tag trigger and one source validator.

- Accept only `vX.Y.Z`, with three decimal components, no leading zeroes, no
  prerelease or build suffix, and a bounded component length.
- Require an annotated tag object that points directly to one commit. Reject a
  lightweight tag, nested tag, or ambiguous resolution.
- Bind and validate the workflow repository, ref, event commit, checked-out commit,
  tag commit, and canonical remote.
- Fetch complete tag history and canonical `main` without persisted checkout
  credentials.
- Require the tag commit to be reachable from canonical `main`.
- Require the tag version to match every repository-declared application,
  workspace, lockfile, bundle short version, and build version that the repository
  owns.
- Require the exact official Sparkle source, repository-owned version, and resolved
  revision. Disable automatic package resolution in the release build.
- Before tag push, require the candidate version to advance every existing remote
  stable-version tag and public stable Release.
- Export the validated commit, version, Sparkle version, and revision to later
  jobs. Recheck the bindings at each privileged boundary.
- Do not let the workflow create its own tag.

Validate the candidate source before its tag is pushed. Once a remote tag exists,
never move, replace, force-update, or reuse it for different source. Correct a
source or build defect on `main`, advance the application version, and create a new
annotated tag.

## Workflow Trust And Serialization

Use one tag-triggered workflow with these ordered owners:

1. a Linux source-validation job;
2. a macOS native test, build, signing, notarization, stapling, and packaging job;
   and
3. a Linux GitHub publisher job.

Apply these controls:

- set workflow permissions to `contents: read` by default;
- grant `contents: write` only to the publisher job;
- set checkout to `persist-credentials: false`;
- pin third-party actions to reviewed immutable commit SHAs;
- set explicit job timeouts, including a bounded notarization wait;
- serialize stable releases through one global `release` concurrency group;
- set `cancel-in-progress: false`; and
- make the publisher depend on successful source validation and macOS packaging.

Use a protected, repository-scoped `release` environment as the final approval and
audit boundary for the publisher. Restrict it to the authorized stable tag pattern
and require the selected reviewer policy. Keep this environment secret-free. The
publisher receives only the ephemeral `GITHUB_TOKEN`, the validated release
artifacts, and non-secret metadata. It must not receive Apple or Sparkle credentials.

Do not add a second Release Preparation, Release Prep, Release Dry Run, or manual
publication lane. A credential-free local publisher `--dry-run` can validate local
assets, but it must make no GitHub request.

Routine pull-request and `main` CI remains repository policy. It can be Linux-only
when the repository accepts later native feedback. It can include macOS when early
feedback justifies the cost. Never weaken the formal tag release's native macOS
tests, build, signing, notarization, or artifact verification because routine CI is
Linux-only.

## Secret And Key Topology

Use these unambiguous ACG Box organization-secret names for shared Developer ID and
notary material:

- `ACG_MACOS_DEVELOPER_ID_APPLICATION_P12_BASE64`;
- `ACG_MACOS_DEVELOPER_ID_APPLICATION_P12_PASSWORD`;
- `ACG_MACOS_NOTARY_API_KEY_ID`;
- `ACG_MACOS_NOTARY_API_ISSUER_ID`; and
- `ACG_MACOS_NOTARY_API_PRIVATE_KEY_P8`.

Use a team App Store Connect API key for `notarytool`. The key ID, issuer ID, and
private `.p8` key form one credential set. This skill does not support Apple ID and
app-specific password authentication. If the team API-key credential set is not
usable, report a live-readiness gap and stop instead of improvising another notary
topology.

The certificate secrets must contain one Developer ID Application identity and its
private key. Do not store a signing-identity label as a secret. Derive the installed
identity from the isolated temporary keychain, then require its certificate class,
validity, private-key presence, and Team ID to match the target adapter.

An organization secret must give the exact target repository effective access.
Visibility `all` is an allowed current topology, not a rule that requires widening.
Visibility `selected` is conforming when it includes the target repository. Judge
any other supported visibility only by effective target access. Report a missing
target grant as drift. Do not report a tighter effective `selected` scope as drift.

Reject a repository or environment secret with the same name as any organization
secret above. GitHub resolves a same-name lower-scope secret before the organization
secret, so shadowing makes provenance ambiguous.

Keep each application's Sparkle private Ed25519 key in that application's
repository under an application-specific name such as
`<APPLICATION>_SPARKLE_PRIVATE_ED_KEY`. Never use a generic organization or
environment `SPARKLE_PRIVATE_ED_KEY`, and never reuse another application's key.

Check the corresponding Sparkle public key into the target repository and embed
that same key in the app. Before appcast generation, derive or verify the public key
from the private secret and fail on a mismatch. A Sparkle public key is product
configuration, not a secret. This plugin contains no application public key.

Use only the ephemeral workflow token for GitHub publication. Do not store a GitHub
token as a release secret. Never print, upload, or place private key or certificate
values in source, logs, fixtures, command arguments, cache entries, or artifacts.
When Sparkle accepts a private key on standard input, use that interface instead of
the deprecated direct-key argument.

## Build Before Credentials And Restore Host State

Run all credential-free release tests and the complete unsigned build before
writing certificate, notary, or Sparkle private material. Bind temporary staging to
the runner-designated temporary directory. Reject unsafe, pre-existing, broad, or
repository-owned staging paths. Expose Apple and Sparkle secrets only to the later
privileged packaging step. Credential-free validation and build steps must not
receive those secrets as environment inputs.

Before changing the user keychain configuration, capture the exact user search list
and default keychain. Install an exit and signal cleanup before the first mutation.
The cleanup must run on every reachable success, failure, timeout, and cancellation
path. It must:

1. restore the exact original user search list;
2. restore the exact original user default keychain;
3. read both values back and fail the run if restoration is incomplete;
4. delete the temporary keychain only after restoration; and
5. remove every decoded certificate, password file, notary `.p8` file, Sparkle-key
   file, upload archive, and other private temporary file.

Deletion of the temporary keychain without search-list and default restoration is
not cleanup.

After the credential-free build:

1. decode the P12 into the isolated staging directory;
2. create and unlock a temporary keychain;
3. make that keychain the sole user search-list keychain;
4. make it the user default keychain before changing its key partition list;
5. import the P12 and require exactly one usable Developer ID Application identity;
6. match the identity and certificate Team ID to the target adapter; and
7. write the notary team API private key only when the notarization step needs it,
   with owner-only permissions.

An Xcode account, a certificate file, or a successful import does not prove that a
usable Developer ID identity exists. Require a valid certificate, its private key,
the expected certificate class, and the adapter's Team ID as separate facts.

## macOS Build And Inside-Out Signing

Use the target repository's supported GitHub-hosted ARM64 macOS runner. Confirm the
runner architecture, selected Xcode and Swift versions, checked-out commit,
validated version, and release configuration before packaging.

Stage one real `.app` bundle. Verify its plist identity, versions, feed,
checked-in Sparkle public key, deployment minimum, architecture, and update settings
before signing.

Require an exact repository-owned Sparkle pin and revision. Do not impose one
Sparkle version across applications. Resolve
`Sparkle.framework/Versions/Current` dynamically as one safe direct-child version
directory. Reject an absolute target, parent traversal, missing target, extra
version directory, second alias, unknown executable, nested app, or unexpected XPC
service.

Enumerate the accepted executable graph. Sign the innermost Mach-O binaries,
helpers, XPC services, frameworks, and other signed bundles before their containers,
then sign the outer app. Preserve entitlements only for a known component that
requires them. Never use `codesign --deep` to sign.

Every signed object must have:

- a valid `Developer ID Application:` authority;
- the target adapter's exact paid Team ID;
- Hardened Runtime;
- a secure timestamp; and
- only its repository-approved entitlements.

Reject Apple Development, Mac App Distribution, ad hoc, expired, revoked, or
unexpected identities; missing or insecure timestamps; a different Team ID; an
unexpected entitlement; and outer `get-task-allow` or
`disable-library-validation` unless exact repository authority and current Apple
requirements prove a narrow exception.

After inside-out signing, inspect every signed object and run strict read-only
verification on the complete graph. The final bundle check must be equivalent to
`codesign --verify --deep --strict --verbose=2`. Treat `--deep` only as verification
after explicit inside-out signing.

## Notarization, Stapling, And Final ZIP Order

Keep the notarization upload archive and the public release ZIP as two different
artifacts with different paths and purposes.

1. After strict signature verification, create one temporary ZIP from the signed,
   unstapled app for Apple notarization. Use an archive method that preserves the
   bundle, resource forks, and symlinks. Mark this artifact as non-public.
2. Submit only that temporary ZIP with `notarytool`, the team API key ID, issuer ID,
   private `.p8` path, a bounded wait, and machine-readable output. Never use
   `--force` to bypass preflight problems.
3. Bind the returned submission ID to the exact source commit and upload artifact.
   Require terminal status `Accepted` from the submit result and a separate
   `notarytool info` readback.
4. Retrieve and parse the completed notarization log even when the status is
   `Accepted`. Fail on an error. Preserve and report material warnings. The log is
   run evidence, not a public release asset.
5. Staple the ticket to the original signed app. A ZIP cannot be stapled directly.
6. Run `stapler validate` on the app. Re-run the complete strict code-signature and
   entitlement checks, then require `spctl --assess --type execute` to accept the
   app as notarized Developer ID software.
7. Only after stapling and Gatekeeper acceptance, create the final public ZIP from
   the stapled app. Never reuse or rename the notarization upload ZIP.
8. Extract the final ZIP into a new clean temporary directory. Recheck its one-app
   root, stapled ticket, strict signature graph, product identity, version, and
   Gatekeeper acceptance.
9. Generate the Sparkle Ed25519 signature and appcast entry from the exact final ZIP
   bytes. Require the appcast length to equal the final ZIP byte length and verify
   the signature with the checked-in public key.
10. Generate the lowercase SHA-256 checksum file from that same final ZIP.

Do not rebuild, re-sign, re-staple, recompress, rename, or otherwise change the ZIP
after Sparkle signature or checksum generation. Remove the temporary notarization
upload archive during cleanup. Never publish it, sign it for Sparkle, or use it as
checksum input.

## Exact Release Assets And Sparkle Trust

Upload exactly three release assets:

1. one repository-named final macOS ZIP that contains one expected `.app` root;
2. `appcast.xml`; and
3. one repository-named `.sha256` file for the final ZIP.

The ZIP validator must bound the entry count, individual and total declared sizes,
path and metadata lengths, plist and XML sizes, and symlink targets. Reject duplicate
members, absolute paths, parent traversal, a second payload root, unexpected file
types, an unsafe Sparkle layout, and XML `DOCTYPE` or `ENTITY` declarations.

The appcast must use the repository's canonical release and download URLs,
validated tag version, exact final ZIP byte length, declared platform and deployment
minimum, and an Ed25519 signature over the exact final ZIP bytes. Verify the
signature with the checked-in public key.

The checksum file must contain the lowercase SHA-256 digest of the exact final ZIP
and its canonical file name in one accepted format. GitHub-generated source links do
not count as uploaded release assets. Do not add source archives, DMGs, PKGs,
installers, or other platform packages to this contract.

## Certificate And Sparkle-Key Lifecycle

Treat the application's checked-in Sparkle public key as a stable installed-client
trust root. Assign an accountable recovery owner for its private key and keep a
protected, tested backup outside the release runner. Do not regenerate the key for
convenience, repository migration, staff change, CI change, or a routine release.

Track the Developer ID certificate's public fingerprint, Team ID, expiry, and
recovery owner in the appropriate protected operations system. Do not create,
export, renew, revoke, or rotate it during an ordinary release. Start a separately
authorized rotation before expiry and prove the replacement identity in a
non-publishing validation lane.

Never rotate the Developer ID certificate and Sparkle Ed25519 key in the same
application update. Sparkle's regular-app fallback permits one trust root to validate
a change in the other, not simultaneous replacement.

Every Sparkle-key migration plan must:

- inventory the oldest supported installed Sparkle version and current trust keys;
- keep the Developer ID certificate stable while the Sparkle key changes;
- use the exact migration path in current Sparkle guidance;
- ship and verify any required transition update before removing the old key;
- test update installation from the oldest supported installed version; and
- retain protected recovery material until adoption evidence closes the migration.

If `SUVerifyUpdateBeforeExtraction` is enabled, current Sparkle guidance can require
a Developer ID-signed DMG to rotate the Ed25519 key. That migration is outside this
ZIP-only skill. Stop and design a separately owned, separately authorized migration;
do not claim DMG support or weaken update verification. For DSA-to-Ed25519 migration,
follow Sparkle's staged dual-key and dual-signature guidance for the installed-client
versions that require it.

When the Developer ID certificate changes, keep the Sparkle key stable and verify a
real update from a currently released version. When the Sparkle key changes, keep
the Developer ID certificate stable. A lost key, compromised key, or revoked
certificate is an incident and migration input, not permission for casual
regeneration or bypass.

## Draft-First Publisher Contract

The publisher must validate the local final asset triplet before its first GitHub
mutation. It must then use this state machine:

1. Read all Releases through bounded pagination and enumerate all remote
   stable-version tags. Reject a new candidate unless it advances the greatest
   existing stable version across public Releases and every other remote stable tag.
2. Find zero or one release for the candidate tag. Reject duplicate same-tag
   releases and conflicting public state.
3. Create one private same-tag draft, or reuse the known private draft.
4. Read all draft assets through bounded pagination. Delete every existing draft
   asset by stable asset ID, including placeholders with missing digests.
5. Upload exactly the required final ZIP, appcast, and checksum. Leave no extra
   uploaded asset.
6. Read back metadata and download every remote asset. Require the uploaded state,
   safe integer size, canonical API and browser URLs, GitHub SHA-256 digest, exact
   byte hash, exact set, and complete artifact validation.
7. Immediately before publication, repeat the remote annotated-tag, direct commit,
   canonical `main` ancestry, complete stable-version, exact draft-ID, metadata,
   and downloaded-byte checks.
8. Make one final state-changing request that sets `draft=false` and
   `make_latest=true`.
9. Read the public release and download its bytes after a successful or uncertain
   publication response.

The final publication request is non-idempotent. Never blindly retry it.

## Bounded GitHub Reconciliation

Bound every read by page count, item count, response bytes, timeout, retry count,
and total delay. Validate pagination links or page transitions. Honor a valid
`Retry-After` value for HTTP 429. Retry only safe reads after a transient network
error or 5xx response.

Do not blindly retry create, delete, upload, or publish requests. When a mutation
response is missing or uncertain, use bounded authoritative reads to decide whether
the intended state exists. Continue only when readback proves one unambiguous state.
If a new draft or public release is temporarily absent from a release listing, use
its known stable ID and bounded convergence. If readback does not converge, stop
further mutations and report the unresolved state. After an uncertain publication
request, do not claim that the release is private or public without authoritative
readback.

An already public same-tag rerun is read-only and idempotent. Validate its remote
metadata and downloaded bytes, then exit successfully. Do not apply the new-release
version gate to that exact public retry, upload replacement assets, or compare the
public ZIP with a newly rebuilt ZIP whose container metadata can differ.

## Version Monotonicity And Recovery

Prevent version downgrade and rollback publication. A new public stable release
must be greater than every current public stable Release and every other remote
stable-version tag. Repeat this check immediately before publication because
another tag or Release can appear while the draft is prepared. An exact already
public same-tag read-only retry remains the only exception.

For a transient safe-read or provider-state failure, rerun the unchanged workflow
only when the current runbook permits it. Let the publisher repair its private draft
and reconcile ambiguous GitHub state through its bounded rules. Reuse an existing
Apple submission only when its stable submission ID and exact upload-artifact
binding prove that reuse is correct; a new notarization submission is a new live
mutation.

For a source, test, build, signing, certificate, notarization, key, metadata, or
artifact defect:

- fix the owning source on `main`;
- advance the version;
- create a new annotated tag; and
- leave the old remote tag unchanged.

Never move a remote tag, lower the version, publish a failed draft manually, delete
a public Release as an ordinary retry, bypass Apple rejection, or ask users to use
Open Anyway. Any exceptional destructive recovery requires exact user authority, a
refreshed remote-state preview, and the target repository's runbook.

## Validation And Evidence

Credential-free contract tests must cover behavior, not exact prose. At minimum,
cover:

- supported Sparkle ZIP scope and explicit rejection of DMG, PKG, and non-Sparkle
  operation;
- detection of Apple Development, Personal Team, timestamp-free, unnotarized, and
  Open Anyway legacy drift;
- stable and invalid SemVer, annotated and lightweight tags, direct and nested tag
  targets, repository/ref/SHA binding, version mismatch, `main` ancestry, and a
  higher existing remote stable tag or public stable Release;
- exact Sparkle source, version, revision, safe dynamic `Current` layout, and
  rejected extra or unsafe framework content;
- build-before-credential order, original keychain state capture, temporary
  keychain order, restoration on every exit path, one-identity policy, inside-out
  signing, Developer ID authority, Hardened Runtime, secure timestamp, target Team
  ID, and entitlement rejection;
- separate notarization and public ZIP paths, bounded `notarytool` submission,
  `Accepted` info and log readback, stapling, stapler validation, strict code-signing
  verification, Gatekeeper acceptance, and final-ZIP-after-stapling order;
- ZIP bounds, duplicate and unsafe members, canonical appcast URLs, key mismatch,
  invalid Ed25519 signatures, checksum format, and exact asset sets;
- effective organization-secret access, conforming `all` and `selected` scope, and
  lower-scope shadow rejection;
- certificate and Sparkle-key lifecycle gates, including rejection of simultaneous
  rotation;
- release and asset pagination, response limits, 429 and 5xx safe-read behavior,
  ambiguous mutations, delayed draft visibility, duplicate releases, late tag or
  version races, final byte races, and one final publish mutation;
- read-only already-public retries and credential-free local dry runs; and
- injected network and command boundaries that make no live mutation.

Static validation and a successful local contract suite prove only the checked-in
adapter. They do not prove Apple account status, a usable Developer ID identity,
notary credentials, hosted runner behavior, protected-environment settings, GitHub
publication, public asset bytes, Gatekeeper behavior on another Mac, or user flows.

For live release acceptance, verify all of these from the public Release:

- the exact annotated tag, source commit, and pipeline revision;
- the workflow's terminal success and attempt history;
- a non-draft, non-prerelease, latest stable Release;
- exactly the final ZIP, appcast, and checksum assets;
- GitHub asset metadata and SHA-256 digests;
- downloaded remote bytes and checksum;
- appcast URL, length, version, and Ed25519 signature;
- the extracted app's stapled ticket, complete strict signature graph, Hardened
  Runtime, secure timestamps, Developer ID identity, and target Team ID;
- Gatekeeper acceptance of the downloaded app; and
- repository-required launch, update, and product smoke tests when separately
  authorized and available.

Report which exact pipeline revision has live proof. Preserve a gap when later
hardening has only checked-in tests, or when certificate, notary, Apple service,
runner, environment, public download, Gatekeeper, or user-flow evidence is
unavailable.

## Current Provider References

Recheck these official sources before a live operation:

- Apple: [Developer ID certificates](https://developer.apple.com/help/account/certificates/create-developer-id-certificates/),
  [Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution),
  [Customizing the notarization workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow),
  [TN3147: Migrating to the latest notarization tool](https://developer.apple.com/documentation/technotes/tn3147-migrating-to-the-latest-notarization-tool),
  and [Resolving common notarization issues](https://developer.apple.com/documentation/security/resolving-common-notarization-issues).
- Sparkle: [Documentation](https://sparkle-project.org/documentation/),
  [Publishing an update](https://sparkle-project.org/documentation/publishing/),
  and [Upgrading to EdDSA from DSA](https://sparkle-project.org/documentation/eddsa-migration/).
- GitHub: [Secrets reference](https://docs.github.com/en/actions/reference/security/secrets),
  [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
  [Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
  [REST releases](https://docs.github.com/en/rest/releases/releases), and
  [REST release assets](https://docs.github.com/en/rest/releases/assets).
