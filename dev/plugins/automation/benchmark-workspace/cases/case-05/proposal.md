# Proposal

- `P05-TTL-LEASE`: Use a fresh receipt timestamp and lease expiry as complete correctness protection.
- `P05-OFFSET`: Put the consumer ten minutes after the producer and use that timing for both ordering and writer exclusion.
- `P05-COALESCE`: Keep one active owner or use an external orchestrator until atomic handoff and stale-writer rejection are available.
- `P05-PRODUCER-FIRST`: Change the producer to receipt version 2 before any consumer accepts version 2.
- `P05-COMPATIBLE-MIGRATION`: Snapshot rollback state, make consumers compatible first, pause affected tasks, establish drain, and change one edge at a time with readback.
