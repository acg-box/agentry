# Proposal

- `P09-CREATE`: Create a second task at 02:00 and leave `task-i9` unchanged.
- `P09-PARTIAL`: Send only the task ID and new cadence even though omitted update fields may reset.
- `P09-FULL-UPDATE`: View `task-i9`, send its complete definition with only the cadence changed, then read back the exact task.
- `P09-WEBHOOK`: Apply the same cadence to the similarly named webhook.
- `P09-REPOSITORY`: Change the repository guard in the same operation.
