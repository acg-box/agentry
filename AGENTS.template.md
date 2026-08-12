## Quality Gates

Use `$quality-gates:design` when a task audits, simplifies, designs, or implements
repository checks, affected-scope selection, CI fan-out, or pre-release
verification. The target repository remains the authority for required behavior,
platform coverage, release policy, and deployment.

Default to the smallest gate that proves the changed risk. Use explicit owners or
changed scope for daily work. Run complete verification only at the repository's
declared integration or release boundary. Do not remove distinct safety, rollback,
platform, migration, artifact, or runtime evidence only to reduce elapsed time.
