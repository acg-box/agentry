# Evidence

- Producer `task-c1` publishes snapshot cycle `YYYY-MM-DD`.
- Consumer `task-c2` requires the snapshot from the same cycle and receipt version 3.
- The target can commit the snapshot and its receipt atomically.
- Join task `task-c3` requires matching receipts from `task-c1` and `task-c4`.
- `task-c4` is paused. No matching receipt exists for the next cycle.
- `task-c5` requires output from `task-c6`, and `task-c6` requires output from `task-c5` for the same cycle.
- No task has permission to run the other task's work directly.
