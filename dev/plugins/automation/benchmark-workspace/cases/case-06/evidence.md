# Evidence

- A new `task-f1` activation can arrive while the prior activation is active.
- The arrival policy is not declared.
- Four activations are already waiting, and the oldest is 90 minutes old.
- Step A charges an external account and is not idempotent.
- Step B writes a report. Step B failed after Step A completed.
- The current retry starts again at Step A.
- The external account allows one active charge operation.
