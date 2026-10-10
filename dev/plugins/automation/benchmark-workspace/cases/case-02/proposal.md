# Proposal

- `P02-GUARD-INDEPENDENT`: Add receipts and leases between `task-b1` and `task-b2` because they start together.
- `P02-ALLOW-INDEPENDENT`: Permit `task-b1` and `task-b2` to overlap and monitor their runtime and failure rate.
- `P02-CAPACITY`: Spread or cap `task-b3` through `task-b7` from the quota and runtime evidence, and select an explicit backlog policy.
- `P02-OVERLAP-CLAIM`: State that the five quota-sharing tasks have been observed running concurrently.
- `P02-SPACING-LOCK`: State that spacing the five tasks by ten minutes guarantees mutual exclusion.
