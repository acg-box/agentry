# Evidence

- The business requirement says 02:30 in `America/New_York` each day.
- The scheduler exposes an RRULE but does not expose timezone, daylight-saving, or missed-run semantics.
- The host can sleep through a scheduled time.
- The workload can accept a stable business-cycle key and reject a repeated cycle.
- The task uses permission label `report-reader`. Its secret value is not needed for review.
- No notification owner or failed-run destination is declared.
