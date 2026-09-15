# ACG Box macOS Sparkle ZIP Release Standard

## Scope And Authority

This standard applies only after the skill's canonical-owner and distribution
checks pass. It defines the shared ACG Box release contract. Each target
repository owns its executable adapter and product identity.

Repository-write authority covers migration and normalization. Publishing one
named version requires release authority for its exact repository, version,
commit, tag push, and workflow. Environment approval, installation, certificate
or Sparkle-key lifecycle changes, secret changes, tag movement, release deletion,
and exceptional manual recovery require their own authority when not already
covered by the request. Preserve granted authority across follow-ups.

## Production Contract

Supported releases use Developer ID Application signing, Hardened Runtime,
secure timestamps, Apple notarization, stapling, strict signature verification,
and Gatekeeper acceptance. Apple Development, Personal Team, ad hoc,
timestamp-free, unnotarized, and Open Anyway distribution are migration drift,
not alternative production policies.

The release binds one immutable annotated stable tag to one commit and version.
Credential-free validation and build precede access to signing secrets. The final
public ZIP contains the stapled app; its exact bytes determine the Sparkle
signature, appcast length, and checksum. Publication uses a private draft and a
protected publisher. Acceptance requires verification of downloaded public assets.

## Target Repository Adapter

Keep product-specific values in the target repository: app and bundle identity,
platform minimum and architecture, version owners and build-number policy, asset
names and URLs, Sparkle source/version/revision and public key, entitlements,
Apple Team ID and Developer ID identity selector, build and test commands, tool
selection, and protected-environment reviewer and tag policy.

Verify the declared signing identity against the imported identity and signed
code. An Xcode account or an Apple Development certificate does not establish a
usable Developer ID identity or the paid Team ID.

GitHub Actions must use checked-in repository workflows and programs. It must
never depend on an installed Codex plugin. Preserve established implementation
owners; choose implementation and tests to satisfy this contract.

## Immutable Source

Use one source validator and accept only annotated `vX.Y.Z` stable tags: decimal
components without leading zeroes, prerelease, or build suffixes. The tag must
point directly to one commit reachable from canonical `main`.

Bind the workflow repository, ref, event commit, checkout, tag commit, and
canonical remote. The version must match all declared application, workspace,
lockfile, and bundle version owners. Pin the official Sparkle source, version,
and revision in the repository; disable automatic package resolution in the
release build. Carry these validated bindings across privileged job boundaries.

Validate before tag push. A new candidate must advance every existing remote
stable tag and public stable Release. Recheck that condition before publication.
The workflow does not create its own tag. Never move or reuse a remote tag for
different source; fix source defects on `main` and release a new version.

## Workflow And Publisher Isolation

Use one tag-triggered workflow with Linux source validation, macOS native tests
and packaging, then a Linux publisher dependent on both preceding jobs.

Use `contents: read` by default, `contents: write` only for the publisher,
`persist-credentials: false` for checkout, immutable reviewed action SHAs, and
explicit job timeouts. Serialize stable releases through one global `release`
concurrency group with `cancel-in-progress: false`.

The publisher uses a protected, repository-scoped `release` environment restricted
to authorized stable tags and the selected reviewer policy. Keep it secret-free:
it receives the ephemeral `GITHUB_TOKEN`, validated assets, and public metadata,
with no Apple or Sparkle credentials.

Do not add a separate Release Preparation, Release Dry Run, or manual publication
lane. A local publisher `--dry-run` validates assets without GitHub requests.
Routine PR and `main` CI can be Linux-only or include macOS under repository
policy; formal release validation always includes native macOS tests and build.

## Secret And Key Topology

Use these organization-secret names for shared signing and notary material:

- `ACG_MACOS_DEVELOPER_ID_APPLICATION_P12_BASE64`;
- `ACG_MACOS_DEVELOPER_ID_APPLICATION_P12_PASSWORD`;
- `ACG_MACOS_NOTARY_API_KEY_ID`;
- `ACG_MACOS_NOTARY_API_ISSUER_ID`; and
- `ACG_MACOS_NOTARY_API_PRIVATE_KEY_P8`.

Notarization uses one team App Store Connect API-key credential set with
`notarytool`. Apple ID and app-specific password authentication are outside this
contract. The P12 contains one Developer ID Application identity and its private
key. Derive and verify the identity from the temporary keychain; do not store a
signing-identity label as a secret.

Organization secrets must grant the exact repository effective access. Both
`all` and `selected` are conforming when access is effective; do not widen a valid
selected scope. Reject same-name repository or environment secrets that shadow
this organization material.

Each application owns a repository secret such as
`<APPLICATION>_SPARKLE_PRIVATE_ED_KEY`. Do not share it between applications or
use a generic organization or environment `SPARKLE_PRIVATE_ED_KEY`. Check the
corresponding public key into the repository, embed it in the app, and verify
that the signing key matches it before appcast generation.

Keep private material out of source, logs, caches, and artifacts. Use Sparkle's
standard-input key interface when available. GitHub publication uses only the
ephemeral workflow token, with no persistent GitHub release secret.

## Build And Signing

Complete credential-free tests and the unsigned build before exposing Apple or
Sparkle secrets to the packaging step. Use isolated temporary staging.

Preserve and restore the original user keychain search list and default keychain
on exit, including failure or cancellation. Verify restoration before deleting
the temporary keychain, and remove private temporary material. Make the temporary
keychain the sole user search-list keychain and default before changing its key
partition list. Require exactly one usable Developer ID identity with the
adapter's Team ID.

Use the repository's supported GitHub-hosted ARM64 macOS runner and tool versions.
Stage one app matching the declared identity, versions, feed, public key,
architecture, deployment minimum, and update settings.

Resolve Sparkle's `Versions/Current` to a safe direct-child version directory and
validate its expected executable graph. Sign known binaries and nested bundles
inside-out, then the outer app. Do not use `codesign --deep` for signing.

Every signed component must have the expected Developer ID authority and Team ID,
Hardened Runtime, secure timestamp, and approved entitlements. Outer
`get-task-allow` or `disable-library-validation` requires an explicit narrow
repository exception supported by current Apple requirements. Verify the complete
signed graph; the final bundle check is equivalent to
`codesign --verify --deep --strict --verbose=2`.

## Notarization And Final Assets

Preserve this artifact order:

1. Verify the signed app and create a separate temporary notarization ZIP.
2. Submit that ZIP with the team API key and a bounded wait. Bind the submission
   ID to its source and upload artifact. Require `Accepted` from submission and
   `notarytool info`; read the log, reject errors, and report material warnings.
3. Staple the original app, validate its ticket, repeat strict signature checks,
   and require Gatekeeper acceptance.
4. Create the final public ZIP from the stapled app. Extract and verify it before
   generating the Sparkle signature, appcast, and checksum from those exact bytes.

Never publish the notarization upload ZIP or modify the final ZIP after signature
and checksum generation. Publish exactly three assets:

- the repository-named final ZIP with one expected `.app` root;
- `appcast.xml`; and
- the repository-named lowercase SHA-256 checksum file for that ZIP.

Validate archive structure before extraction. The appcast must bind the canonical
release/download URLs, version, platform minimum, final ZIP byte length, and
Ed25519 signature verified with the checked-in public key. GitHub-generated source
links do not count as uploaded assets.

## Draft Publication And Recovery

Validate local assets before GitHub mutation. Create or reuse one private draft
for the candidate tag; replace its assets with exactly the final asset triplet.
Reject duplicate same-tag releases and conflicting public state.

Before publication, verify the exact draft and uploaded assets by metadata and
downloaded bytes, including canonical URLs, sizes, GitHub SHA-256 digests, and
artifact validity. Recheck the annotated tag, commit, `main` ancestry, and version
advance. Publish with one final `draft=false`, `make_latest=true` mutation.
Resolve an uncertain publication result from authoritative state before any
further write. Report unresolved publication state without claiming that the
release is private or public.

An already public same-tag rerun is read-only: verify its remote metadata and
assets. Do not apply the new-version gate, replace public assets, or compare them
against a fresh rebuild whose archive metadata can differ.

Use the target runbook for recovery. Reuse an Apple submission only when its ID
and exact upload-artifact binding establish that it is the same candidate.
Do not bypass notarization or environment approval, manually publish a failed
draft, or delete a public release as routine recovery.

## Trust-Root Changes

Keep protected recovery ownership for the Developer ID certificate and each
application's Sparkle private key. Routine releases do not create or rotate them.
Never change the Developer ID certificate and Sparkle key in the same update.

For an authorized rotation, follow current Sparkle guidance and test the update
from supported installed versions before retiring old trust material. Keep the
other trust root stable. If `SUVerifyUpdateBeforeExtraction` requires a signed
DMG for key migration, that migration is outside this ZIP-only skill. Legacy
DSA-to-Ed25519 transitions use the provider's staged migration path.

## Acceptance

Validate changed repository behavior against the relevant release contracts.
Select tests for the actual change.

Live acceptance binds the exact pipeline revision, successful workflow, immutable
tag, and latest public stable Release. Verify downloaded asset hashes, appcast
signature and metadata, extracted app identity and version, stapled ticket,
complete signature graph, and Gatekeeper acceptance. Run repository-required app
or update checks when authorized. Local tests alone do not establish live release
success; report any missing live evidence.

## Provider References

Consult current provider guidance for implementation details:

- Apple: [Developer ID](https://developer.apple.com/help/account/certificates/create-developer-id-certificates/),
  [notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution),
  and [custom workflows](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow).
- Sparkle: [publishing](https://sparkle-project.org/documentation/publishing/)
  and [key migration](https://sparkle-project.org/documentation/eddsa-migration/).
- GitHub: [workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
  [environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
  [Releases](https://docs.github.com/en/rest/releases/releases), and
  [assets](https://docs.github.com/en/rest/releases/assets).
