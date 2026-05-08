# MacroManager Consolidated Audit Logs

## Summary Table

| Issue Name | Brief Description | Criticality | Status |
| :--- | :--- | :--- | :--- |
| [Double DuckDuckGo requests](#double-duckduckgo-requests) | Redundant network calls for identical HTML | Medium | [FIXED] |
| [No `source` column in foods table](#no-source-column-in-foods-table) | Cannot audit nutrition data origin | Medium | [FIXED] |
| [Hardcoded prompt in `find_source_of_truth`](#hardcoded-prompt-in-find_source_of_truth) | Prompt not externalized in `prompts.yaml` | Medium | [FIXED] |
| [Wiki documentation out of sync](#wiki-documentation-out-of-sync-with-code) | Docs reference dead code/old architecture | Medium | [PENDING] |
| [Singleton pattern breaks testability](#singleton-pattern-breaks-testability) | `DatabaseManager` singleton hinders isolated tests | Medium | [FIXED] |
| [Schema mismatch across old and new modules](#schema-mismatch-across-old-and-new-modules) | Old modules create incompatible FTS5 schema | Medium | [FIXED] |
| [`upsert_food` FTS5 DELETE incompatibility](#upsert_food-fts5-delete-incompatibility) | Redundant `DELETE` call on content-less FTS5 table | Medium | [FIXED] |
| [Debug scripts in tests/ folder](#debug-scripts-in-tests-folder) | Non-pytest scripts in `tests/` directory | Low | [FIXED] |
| [Frontend uses synchronous `requests`](#frontend-uses-synchronous-requests) | Streamlit uses sync calls for async backend | Low | [FIXED] |
| [Empty directories](#empty-directories) | Unused `templates/` and `wiki/entities/` | Low | [FIXED] |
| [`fiber` key inconsistency](#fiber-key-inconsistency-between-data-sources) | Return formats differ between web search methods | Low | [FIXED] |
| [Race condition in `asyncio.gather`](#race-condition-in-asyncio.gather-with-shared-mutable-state) | Concurrent mutation of shared state dict/list | Critical | [FIXED] |
| [Database drops foods table](#database-drops-and-re-creates-foods-table-on-every-startup) | Learned data wiped on every restart | Critical | [FIXED] |
| [Missing recipe expansion](#missing-recipe-expansion-in-new-extraction-pipeline) | Complex dishes not decomposed into ingredients | Critical | [FIXED] |
| [Dead code in `get_nutrition_data`](#dead-code-54-lines-after-return-none-at-line-243) | Unreachable blocks in `foodbank.py` | Critical | [FIXED] |
| [`POST /verify-queue` timestamp](#post-verify-queue-never-updates-sync_timestamp) | Manual sync doesn't update UI timestamp | Critical | [FIXED] |
| [Dead code - orphaned modules](#dead-code-700-lines-of-orphaned-modules) | Superceded `app/parser.py`, `app/foodbank.py`, `app/database.py` | High | [FIXED] |
| [Missing dependencies](#missing-dependencies-in-requirements.txt) | `httpx` and `pyyaml` not in `requirements.txt` | High | [FIXED] |
| [Crash bug in `get_nutrition_data`](#crash-bug-in-get_nutrition_data-internal-estimate-fallback) | KeyError in internal estimate prompt path | High | [FIXED] |
| [Heartbeat `sync_timestamp`](#heartbeat-updates-sync_timestamp-even-when-verified_count-0) | Timestamp updated even if no items processed | High | [FIXED] |
| [Offline DB-cached return without queueing](#when-offline-db-cached-items-with-verified0-are-returned-without-queueing) | Unverified cached items never get verified | High | [FIXED] |
| [Double-upsert race](#find_source_of_truth-does-its-own-upsert_food-internally) | Redundant DB writes during verification | High | [FIXED] |
| [No retry limit on `pending_verification`](#no-retry-limit-on-pending_verification) | Fake items cause infinite 60s retries | Medium | [FIXED] |
| [`sync_timestamp` in heartbeat call order](#sync_timestamp-in-heartbeat-is-called-after-process_verification_queue-completes) | Timestamp updated before processing check | Medium | [FIXED] |
| [SQLite connection not thread-safe](#sqlite-connection-not-thread-safe) | Potential `ProgrammingError` under concurrent load | Medium | [FIXED] |
| [No in-request caching](#no-in-request-caching-for-web-lookups) | Redundant web fetches for same ingredient in one parse | Low | [FIXED] |
| [New httpx AsyncClient per request](#new-httpx-asyncclient-created-per-request) | Missing connection pooling in web methods | Low | [FIXED] |
| [`httpx.AsyncClient` connection pooling](#httpx.asyncclient-created-fresh-on-every-is_network_available) | Per-call client creation in sync methods | Low | [FIXED] |
| [Heartbeat startup sleep](#heartbeat-sleeps-60s-on-startup-before-first-check) | Cold start delay for first sync | Low | [FIXED] |
| [No logging/metrics on `process_verification_queue`](#no-loggingmetrics-on-process_verification_queue-return-value) | No visibility into verification success rate | Low | [FIXED] |

---

## Detailed Audit Logs

### Race condition in `asyncio.gather` with shared mutable state
- **Files:** `app/services/extraction.py`
- **Issue Detail:** Multiple coroutines mutate the same `state` dict and `parsed_items` list concurrently via `asyncio.gather`. Since dict/list mutations are non-atomic, this leads to data corruption and lost macro values.
- **Fix Detail:** Restructured `_process_base_ingredient` to return a tuple `(macro_delta, food_item)` instead of mutating shared state. Aggregated results sequentially after `asyncio.gather` completes.

### Database drops and re-creates foods table on every startup
- **Files:** `app/services/database.py`
- **Issue Detail:** `_init_foodbank` executed `DROP TABLE IF EXISTS foods`, wiping all learned nutrition data on every application restart.
- **Fix Detail:** Replaced `DROP TABLE` with `CREATE VIRTUAL TABLE IF NOT EXISTS`. Added a check to seed initial data only if the table is empty.

### Missing recipe expansion in new extraction pipeline
- **Files:** `app/services/extraction.py`
- **Issue Detail:** The `parse` method processed all items as base ingredients, ignoring the recipe system. Complex dishes were treated as monolithic items.
- **Fix Detail:** Reintroduced `foodbank.get_recipe()` check. Implemented `_expand_recipe` to decompose dishes into base ingredients and calculate scaled macros before parallel processing of remaining base items.

### Dead code (54 lines) after `return None` at line 243
- **Files:** `app/services/foodbank.py`
- **Issue Detail:** A large block of unreachable code existed after a `return None` in the `get_nutrition_data` method.
- **Fix Detail:** Removed the unreachable code blocks to reduce bloat and confusion.

### `POST /verify-queue` never updates `sync_timestamp`
- **Files:** `app/api.py`
- **Issue Detail:** The manual sync trigger executed the processing queue but failed to update the `sync_status` table, leaving the UI stale.
- **Fix Detail:** Wrapped the sync process and timestamp update into a single method `run_sync_cycle()` and called it from the API endpoint.

### Dead code - 700+ lines of orphaned modules
- **Files:** `app/parser.py`, `app/foodbank.py`, `app/database.py`
- **Issue Detail:** Original monolithic modules superceded by the `services/` architecture remained in the codebase.
- **Fix Detail:** Deleted the three orphaned files and updated any remaining legacy test imports.

### Missing dependencies in requirements.txt
- **Files:** `requirements.txt`
- **Issue Detail:** `httpx` and `pyyaml` were imported in the code but not declared in the dependencies file.
- **Fix Detail:** Added `httpx` and `pyyaml` to `requirements.txt`.

### Crash bug in `get_nutrition_data` internal estimate fallback
- **Files:** `app/services/foodbank.py`
- **Issue Detail:** A `KeyError` occurred because the code tried to access `self.prompts['foodbank']['internal_estimate']` when `self.prompts` was already the `foodbank` sub-dictionary.
- **Fix Detail:** Corrected the access path to `self.prompts['internal_estimate']`.

### heartbeat updates `sync_timestamp` even when `verified_count == 0`
- **Files:** `app/api.py`
- **Issue Detail:** The heartbeat task updated the sync timestamp every 60s regardless of whether any items were actually verified, misleading the user.
- **Fix Detail:** Modified `run_sync_cycle` to only trigger `update_sync_timestamp()` if the number of verified items is greater than zero.

### When offline, DB-cached items with `verified=0` are returned without queueing
- **Files:** `app/services/foodbank.py`
- **Issue Detail:** Unverified cached data was returned during offline mode without being added to the `pending_verification` queue.
- **Fix Detail:** Added a call to `queue_for_verification(name)` when returning cached data with `verified == 0` while offline.

### find_source_of_truth does its own `upsert_food` internally
- **Files:** `app/services/foodbank.py`
- **Issue Detail:** Both the search function and the verification queue processor were performing `upsert_food` calls, creating a redundant write race.
- **Fix Detail:** Added an `upsert` parameter to `find_source_of_truth` to disable internal DB writes when called from the verification queue.

### No retry limit on `pending_verification`
- **Files:** `app/services/foodbank.py`
- **Issue Detail:** Fake or non-existent food items stayed in the queue forever, causing infinite retries every 60s.
- **Fix Detail:** Added a `retry_count` column to the `pending_verification` table and implemented a check to remove items exceeding `MAX_RETRIES` (5).

### `upsert_food` FTS5 DELETE incompatibility
- **Files:** `app/services/foodbank.py`
- **Issue Detail:** Using `DELETE FROM foods WHERE name = ?` is redundant and potentially problematic for content-less FTS5 tables where `INSERT OR REPLACE` handles updates.
- **Fix Detail:** Replaced `DELETE` + `INSERT` with a single `INSERT OR REPLACE` using a subquery to resolve the `rowid`, ensuring updates occur without redundant calls or record duplication.

### `sync_timestamp` in heartbeat is called after `process_verification_queue` completes
- **Files:** `app/api.py`
- **Issue Detail:** The sequence of calls in the heartbeat task didn't properly verify if processing occurred before updating the timestamp.
- **Fix Detail:** Consolidated the logic into `run_sync_cycle` to ensure the timestamp is only updated upon successful verification.

### SQLite connection not thread-safe
- **Files:** `app/services/database.py`
- **Issue Detail:** Concurrent access from the heartbeat task and API requests could cause `sqlite3.ProgrammingError`.
- **Fix Detail:** Added `check_same_thread=False` to all `sqlite3.connect` calls in `DatabaseManager`.

### No in-request caching for web lookups
- **Files:** `app/services/extraction.py`
- **Issue Detail:** Repeated ingredients in a single meal led to redundant web searches for the same item.
- **Fix Detail:** Implemented `self.foodbank_cache` in `ExtractionService` to store and reuse nutrition data for the duration of a single `parse` call.

### New httpx AsyncClient created per request
- **Files:** `app/services/foodbank.py`
- **Issue Detail:** Creating a new `AsyncClient` for every web request increased latency and resource usage.
- **Fix Detail:** instantiated a single `self.http_client` in `FoodbankService.__init__` to reuse connections across all requests.

### `httpx.AsyncClient` created fresh on every `_is_network_available`
- **Files:** `app/services/foodbank.py`
- **Issue Detail:** Redundant client creation in the heartbeat network check and web fetch methods.
- **Fix Detail:** Transitioned all network calls to use the shared `self.http_client`.

### heartbeat sleeps 60s on startup before first check
- **Files:** `app/api.py`
- **Issue Detail:** The heartbeat loop waited 60s before the first sync, causing a delay on server start.
- **Fix Detail:** [FIXED] Moved the sleep call to the end of the loop so the first check runs immediately.

### No logging/metrics on `process_verification_queue` return value
- **Files:** `app/services/foodbank.py`
- **Issue Detail:** The system had no visibility into how many items were successfully verified per cycle.
- **Fix Detail:** Updated `process_verification_queue` to return the `verified_count` and added logging in `run_sync_cycle`.

### Double DuckDuckGo requests for same item
- **Files:** `app/services/foodbank.py`
- **Issue Detail:** `find_source_of_truth` and `search_web_for_food` both fetch the same HTML content separately.
- **Fix Detail:** Refactored `get_nutrition_data` to fetch HTML once and pass it as an optional argument to both extraction methods.

### No `source` column in foods table
- **Files:** `app/services/database.py`, `app/services/foodbank.py`
- **Issue Detail:** Nutrition data is persisted without the source URL, making auditing impossible.
- **Fix Detail:** Added `source` UNINDEXED column to FTS5 `foods` table. Updated `upsert_food` and `find_source_of_truth` to persist the source URL.

### Hardcoded prompt in `find_source_of_truth`
- **Files:** `app/services/foodbank.py`
- **Issue Detail:** The validator prompt is hardcoded in Python instead of being in `prompts.yaml`.
- **Fix Detail:** Externalized the prompt to `prompts.yaml` under `foodbank.source_of_truth` and updated the service to load it dynamically.

### Wiki documentation out of sync with code
- **Files:** `wiki/logic/`
- **Issue Detail:** Wiki pages reference deleted files and outdated architectural patterns (e.g., missing async details).
- **Fix Detail:** [PENDING] Comprehensive update of all wiki pages to match the current implementation.

### Singleton pattern breaks testability
- **Files:** `app/services/database.py`
- **Issue Detail:** `DatabaseManager` singleton prevents creating isolated DB instances for concurrent tests.
- **Fix Detail:** Removed `__new__` override to allow standard instantiation and isolated database managers.

### Schema mismatch across old and new modules
- **Files:** `scripts/ingest_csv.py`
- **Issue Detail:** CSV ingestion script uses an old schema missing the `verified` column.
- **Fix Detail:** Updated `ingest_csv.py` to include `verified` and `source` columns in FTS5 table creation and INSERT statements. Added CLI argument support for non-interactive testing.

### Debug scripts in tests/ folder
- **Files:** `tests/`
- **Issue Detail:** Live-network debug scripts are mixed with unit tests.
- **Fix Detail:** Moved non-pytest scripts to a dedicated `debug/` folder.

### Frontend uses synchronous `requests`
- **Files:** `app/frontend.py`
- **Issue Detail:** Use of `requests` in Streamlit is inconsistent with the async backend.
- **Fix Detail:** Replaced `requests` with `httpx` and wrapped async calls in `asyncio.run()` to maintain compatibility with Streamlit's synchronous execution model.

### Empty directories
- **Files:** `templates/`, `wiki/entities/`
- **Issue Detail:** Unused directories clutter the project root.
- **Fix Detail:** Removed empty `templates/` and `wiki/entities/` directories.

### `fiber` key inconsistency between data sources
- **Files:** `app/services/foodbank.py`, `prompts/prompts.yaml`
- **Issue Detail:** Different web search methods return fiber in different JSON structures (flat vs nested).
- **Fix Detail:** Updated `web_search` prompt to return macros at the top level and removed normalization logic in `get_nutrition_data` to ensure all paths return a uniform flat dictionary.
