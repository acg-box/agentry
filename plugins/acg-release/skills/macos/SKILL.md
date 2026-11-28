---
name: macos
description: Audit or operate Developer ID releases on GitHub for acg-box macOS projects. Covers Sparkle app ZIPs, signed installer PKGs with a repository release procedure, and recovery from interrupted Apple notarization.
---

# ACG Box macOS Releases

Verify the canonical GitHub owner from the remote and provider metadata. Use
this skill for `acg-box` repositories. Within that scope, select the release
procedure from the product and assets declared in the target repository.

- For one regular Sparkle-enabled app distributed in a ZIP, use the
  [Sparkle ZIP standard](references/standard.md#sparkle-zip-releases).
- For a Developer ID installer PKG distributed on GitHub, follow the
  [PKG procedure](references/standard.md#installer-pkg-releases) and the target
  repository's release commands. A repository can publish from a local Mac.
- For other formats or an unresolved owner, report the applicability gap before
  accessing signing material.

For either format, use the [notarization recovery procedure](references/standard.md#notarization-recovery)
when Apple reports an agreement error or the result of a submission is uncertain.

Apply the [authorization rules](references/standard.md#scope-and-authority).
An authorized release of a named version can cover its tag and publication.
Check existing authority separately for installation, account agreements,
environment approvals and changes to keys or secrets. Use a read-only audit when
mutation authority is unclear. The target repository owns the executable
implementation, product identity and tests.
