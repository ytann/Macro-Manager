# Offline Sync Queue

## Flow
 
```
User Input -> ExtractionService.parse()
  -> FoodbankService.get_nutrition_data(name)
     -> [OFFLINE] -> DB-cached data (if exists) / internal_estimate -> queue_for_verification
     -> [ONLINE]  -> find_source_of_truth / search_web_for_food
 
Heartbeat (60s Pulse)
  -> _is_network_available()
  -> get_pending_count() > 0
  -> run_sync_cycle() -> process_verification_queue() (Auto-drains pending_verification table) -> update_sync_timestamp()
 
Manual Trigger
  -> POST /verify-queue -> background_tasks(run_sync_cycle)
```

## get_nutrition_data Resolution Order

1. **L1 Cache Lookup**: In-memory dictionary check.
2. **DB lookup** via FTS5 (exact name + alias + fuzzy word match). If `verified=1`, return immediately.
3. **Network check** (`_is_network_available` — HEAD request to `https://1.1.1.1`)
4. **[OFFLINE]** Return cached data if available (queue unverified items). Else call `internal_estimate` (LLM guess), persist with `verified=0`, queue for later verification.
5. **[ONLINE]** If DB had unverified data or was missing, try `find_source_of_truth` (authoritative web) -> `search_web_for_food` (general web) -> `internal_estimate` (LLM fallback).

## Verification Queue

Schema: `pending_verification (name TEXT PRIMARY KEY, retry_count INTEGER DEFAULT 0)`

- `queue_for_verification(name)` — `INSERT OR REPLACE` preserving existing `retry_count`
- `process_verification_queue()` — processes pending items:
  - Skip items with `retry_count >= MAX_RETRIES (5)` and remove them
  - Increment `retry_count` before each attempt
  - Call `find_source_of_truth(name, upsert=False)` to get authoritative data
  - If confidence High/Medium: upsert with `verified=1`, remove from queue
  - If Low confidence or no data: leave in queue with incremented retry

## run_sync_cycle()

Wraps `process_verification_queue()` — only calls `update_sync_timestamp()` if items were actually verified.

## API Endpoints
 
- `GET /pending-count` — number of queued items
- `GET /sync-status` — last sync timestamp
- `POST /verify-queue` — triggers `run_sync_cycle` as background task
- **Lifespan Shutdown** — calls `foodbank_service.close()` to release HTTP connection pools


## Configuration

- `MAX_RETRIES = 5` — class attribute on `FoodbankService`
- Heartbeat interval: 60s (first check runs immediately on startup)
- Network check timeout: 1.5s
- Shared `httpx.AsyncClient` for connection pooling
- SQLite `check_same_thread=False` for concurrent heartbeat + API access