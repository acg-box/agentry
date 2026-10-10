# Proposal

- `P06-PARALLEL`: Use parallel arrival handling by default because the schedule fired again.
- `P06-POLICY`: Select skip, coalesce, queue, or replace from the service objective, cap backlog age, and define overrun handling.
- `P06-RETRY`: Retry the complete task from Step A without another guard.
- `P06-CHECKPOINT`: Make Step A idempotent or resume from a durable checkpoint after Step A.
- `P06-SPACING`: Move the schedule by fifteen minutes and state that partial failure and replay are now safe.
