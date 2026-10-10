# Proposal

- `P03-OFFSET`: Schedule `task-c2` five minutes after `task-c1` and treat the offset as dependency order.
- `P03-RECEIPT`: Require `task-c2` to verify the exact cycle and receipt version and to fail closed when either differs.
- `P03-FANIN`: Let `task-c3` proceed when either one of its two inputs is fresh.
- `P03-PAUSED`: Keep `task-c3` inactive until a matching `task-c4` receipt exists, and report the paused producer without claiming observed data corruption.
- `P03-CYCLE`: Keep the `task-c5` and `task-c6` cycle because their start times alternate.
