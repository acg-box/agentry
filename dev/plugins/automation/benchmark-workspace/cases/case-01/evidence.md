# Evidence

- The Scheduled view was exported from one laptop at 2026-06-15T14:00:00Z.
- The export contains tasks `task-a1` and `task-a2`.
- A second laptop was offline and could not be inspected.
- An owner declares one webhook and one external cron job. The available tool cannot read either surface.
- A diagnostic cache contains row `cache-old-7`, which is absent from the Scheduled view. The cache is not an authoritative scheduler surface.
- `task-a1` and `task-a2` have similar names and start times. They write to different reports for different business units.
- Permission names are visible. Secret values are not required for this review.
