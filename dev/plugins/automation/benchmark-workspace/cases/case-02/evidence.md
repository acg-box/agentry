# Evidence

- `task-b1` and `task-b2` both start at 01:00.
- They are read-only, use different targets, use different quotas, and each has a p95 runtime of 8 minutes.
- Capacity is sufficient for both tasks. No dependency is declared.
- `task-b3` through `task-b7` also start at 01:00.
- Those five tasks share an API quota that permits two active requests. Their p95 runtime is 35 minutes.
- Start records exist for all seven tasks. End, queue, and overlap records are unavailable.
