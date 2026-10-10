# Evidence

- `task-d1` and `task-d2` are independent but write the same logical ledger record.
- The ledger supports a transactional claim with an idempotency key and a monotonic fencing token on every write.
- The ledger rejects a write whose fencing token is older than the current token.
- A proposed lock file would exist only inside each task's separate worktree.
- A lease can expire while a slow writer is still active.
- The owner can use one active writer if the transactional protocol is not deployed.
