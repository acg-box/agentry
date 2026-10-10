# Proposal

- `P04-DEPENDENCY`: Model `task-d1` as a producer and `task-d2` as its consumer only because both write the ledger.
- `P04-LOCAL-LOCK`: Use one lock file in each worktree as cross-worktree exclusion.
- `P04-FENCING`: Use the ledger's idempotency key, transactional claim, and monotonic fencing check on every write.
- `P04-LEASE`: Treat lease expiry by itself as proof that the older writer cannot write.
- `P04-ONE-OWNER`: Keep only one active writer until the target-enforced protocol is available.
