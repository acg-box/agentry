# Evidence

- This is a one-time database migration review.
- The accepted requirement adds a non-null `region_code` column after a backfill.
- The proposal first adds a nullable column, backfills all rows, validates the result, and then adds the non-null constraint.
- No recurring task, scheduler, event trigger, monitor, or automation is in scope.
