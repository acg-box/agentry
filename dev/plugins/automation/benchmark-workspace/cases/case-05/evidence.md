# Evidence

- `task-e1` produces an index, and `task-e2` consumes that index for the same cycle.
- Both tasks can also update the same index metadata row.
- The index object and its success receipt are stored by separate non-transactional operations.
- A crash can occur after the object write and before the receipt write, or after the receipt write and before the object is visible.
- The metadata store has leases but does not reject writes from an older lease holder.
- Consumers currently accept receipt version 1. The producer proposal changes directly to version 2.
- Group updates are not atomic. Supported run evidence can show when active work has drained.
