---
name: macos
description: Use when auditing, adapting, or operating Developer ID-notarized Sparkle macOS ZIP releases for repositories whose canonical GitHub owner is acg-box. Excludes other owners, DMG, PKG, and non-Sparkle distribution.
---

# ACG Box macOS Releases

Resolve the canonical GitHub owner from the authoritative remote and provider
metadata before release work. Continue only for `acg-box` repositories that
publish one regular Sparkle-enabled macOS app in a GitHub Release ZIP. Otherwise
stop as not applicable, without adoption guidance or use of ACG Box signing and
secret topology. Unresolved ownership is an applicability gap.

Use the [release standard](references/standard.md) as the canonical team policy.
Read it in full for a complete release audit, migration, or operation. For a
focused question or repair, read the relevant sections and their dependencies.
Use current provider documentation for tool and API behavior.

Repository changes, release publication, environment approval, installation, and
certificate, key, or secret changes have separate authorization boundaries. Use
existing authority for the requested work; default to a read-only audit when
mutation authority is unclear. A request to publish one named version can cover
its exact tag push and workflow follow-through, but does not authorize trust-root
rotation or changes to environment rules.

The standard owns release requirements. The target repository owns product
identity, executable implementation, and tests. Complete the requested scope and
report the result, relevant evidence, and remaining gaps.
