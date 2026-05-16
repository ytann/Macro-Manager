# MacroManager Consolidated Audit Logs

## Summary Table

| Issue Name | Brief Description | Criticality | Status |
| :--- | :--- | :--- | :--- |
| [Nutritional Resolution Silent Failures](#nutritional-resolution-silent-failures) | Items extracted but all resolution paths fail, returning 0 calories | High | [FIXED] |
| [Fragile Internal Nutrition Estimates](#fragile-internal-nutrition-estimates) | `internal_estimate` frequently returns `unknown` for regional foods | Medium | [FIXED] |
| [Web Search Precision for Regional Foods](#web-search-precision-for-regional-foods) | Generic search results for specific regional dishes | Medium | [FIXED] |
| [Complex and Inefficient Database Calls in FoodbankService](#complex-and-inefficient-database-calls-in-foodbankservice) | `FoodbankService` uses verbose, repetitive `asyncio.to_thread` for db calls | High | [FIXED] |
| [No Pydantic validation for Onboarding output](#no-pydantic-validation-for-onboarding-llm-output) | `OnboardingService` uses defaults on LLM parse failure | Medium | [FIXED] |
| [Wiki Architecture out of sync](#wiki-architecture-out-of-sync-phase-5) | `Architecture.md` missing Onboarding and updated FTS5 schema | Low | [FIXED] |
| [Vision Client connection overhead](#vision-client-connection-overhead) | `vision_client.py` creates fresh connection per post | Low | [FIXED] |
| [Audit Logic duplication](#audit-logic-historical-duplication) | `audit_logic.md` preserves steps already marked FIXED | Low | [FIXED] |
| [Database still drops foods table on startup](#database-still-drops-foods-table-on-startup) | `DROP TABLE IF EXISTS` regression — data wiped every restart | Critical | [FIXED] |
| [Verification prompt `KeyError`](#verification-prompt-keyerror-on-content-placeholder) | `{content}` placeholder in prompt but not passed to `.format()` | Critical | [FIXED] |
| [`NameError` when all items are recipes](#nameerror-in-extraction-when-all-items-are-recipes) | `results` undefined when no base ingredients | Critical | [FIXED] |
| [`httpx.AsyncClient` never closed](#httpxasynclient-never-closed-in-foodbankservice) | Resource leak — no `close()` or `__del__` on shared client | High | [FIXED] |
| [`seed_db` bare `INSERT OR REPLACE` into FTS5](#seed_db-bare-insert-or-replace-into-fts5) | Missing rowid subquery — duplicate records in FTS5 table | High | [FIXED] |
| [Frontend creates new `AsyncClient` per call](#frontend-creates-new-asynclient-per-request) | No connection pooling in Streamlit frontend | Medium | [FIXED] |
| [`upsert_food` hardcodes `is_complete_protein=0`](#upsert_food-hardcodes-is_complete_protein0) | Cannot persist complete protein data from web search | Medium | [FIXED] |
| [Duplicate seed data in two locations](#duplicate-seed-data-in-two-locations) | Identical food lists in `_init_foodbank` and `seed_db` | Low | [FIXED] |
| [`FoodLogSchema.md` wiki page out of sync](#foodlogschema-wiki-page-out-of-sync) | Missing `verified` field and `GoalRequest` in wiki | Low | [FIXED] |
| [No client cleanup on app shutdown](#no-asynclient-cleanup-on-app-shutdown) | `httpx.AsyncClient` not closed in lifespan handler | Low | [FIXED] |
| [Double DuckDuckGo requests](#double-duckduckgo-requests) | Redundant network calls for identical HTML | Medium | [FIXED] |
| [No `source` column in foods table](#no-source-column-in-foods-table) | Cannot audit nutrition data origin | Medium | [FIXED] |
| [Hardcoded prompt in `find_source_of_truth`](#hardcoded-prompt-in-find_source_of_truth) | Prompt not externalized in `prompts.yaml` | Medium | [FIXED] |
| [Wiki documentation out of sync](#wiki-documentation-out-of-sync-with-code) | Docs reference dead code/old architecture | Medium | [FIXED] |
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
| [Duplicated Code in Meal Logging](#duplicated-code-in-meal-logging) | `log_meal` and `log_vision_meal` have near-identical db insertion logic | Medium | [FIXED] |
| [Redundant Web Searches](#redundant-web-searches-in-foodbankservice) | `search_web_for_food` and `find_source_of_truth` both fetch web pages | Medium | [FIXED] |
| [Inefficient DB Seeding](#inefficient-database-seeding) | `seed_db` calls `upsert_food` in a loop instead of `executemany` | Low | [FIXED] |
| [Hardcoded Queries](#hardcoded-sql-and-search-queries) | SQL and web search queries are hardcoded in services | Low | [FIXED] |
| [Inconsistent Logging](#inconsistent-logging-and-error-handling) | `print()` used for debugging; inconsistent error handling | Low | [FIXED] |
| [No Pydantic validation for Onboarding output](#no-pydantic-validation-for-onboarding-llm-output) | `OnboardingService` uses defaults on LLM parse failure | Medium | [FIXED] |
| [Wiki Architecture out of sync](#wiki-architecture-out-of-sync-phase-5) | `Architecture.md` missing Onboarding and updated FTS5 schema | Low | [FIXED] |
| [Vision Client connection overhead](#vision-client-connection-overhead) | `vision_client.py` creates fresh connection per post | Low | [FIXED] |
| [Audit Logic duplication](#audit-logic-historical-duplication) | `audit_logic.md` preserves steps already marked FIXED in logs | Low | [FIXED] |
| [Medical Firewall Bypass](#medical-firewall-bypass) | Copilot may provide medical advice or ignore safety boundaries | Critical | [FIXED] |
| [Extraction Crash on Empty Input](#extraction-crash-on-empty-input) | Calling parse with empty text causes ValueError crash | High | [FIXED] |
| [Missing Voice Correction in Extraction](#missing-voice-correction-in-extraction) | Voice logs not normalized before extraction | Medium | [FIXED] |
| [Planner Service Architecture](#planner-service-architecture) | Router -> Knowledge -> Copilot flow and safety fallbacks | Medium | [FIXED] |


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

### Database still drops foods table on startup
- **Files:** `app/services/database.py:69`
- **Issue Detail:** `_init_foodbank` executed `DROP TABLE IF EXISTS foods` on every startup. This was marked `[FIXED]` in a prior audit (issue #19) but the code regressed — the `DROP TABLE` returned. All learned nutrition data was destroyed on every application restart.
- **Fix Detail:** Removed `cursor.execute("DROP TABLE IF EXISTS foods")`. Changed `CREATE VIRTUAL TABLE foods USING fts5(...)` to `CREATE VIRTUAL TABLE IF NOT EXISTS foods USING fts5(...)`. The seed-data guard (`COUNT(*) == 0`) already prevents re-seeding on restart. Verified with `tests/ISSUE_DBDROP_unit_persist.py`.

### Verification prompt `KeyError` on `{content}` placeholder
- **Files:** `prompts/prompts.yaml:43-44`, `app/services/extraction.py:37`
- **Issue Detail:** The `extraction.verification` prompt template had a stray `HTML:\n    {content}` at the end — a copy-paste from the `web_search` prompt. The Python code called `.format(text=text, found_details=found_details)` with no `content` kwarg, causing `KeyError: 'content'`. The exception was silently caught by an `except` block, making the verification guardrail effectively dead.
- **Fix Detail:** Removed the stray `HTML:` and `{content}` lines from the `verification` prompt in `prompts.yaml`. Verified with `tests/ISSUE_KEYERROR_unit_verify.py`.

### `NameError` in extraction when all items are recipes
- **Files:** `app/services/extraction.py:205-214`
- **Issue Detail:** `results` was only assigned inside `if base_tasks:` on line 206. If every item in a meal is a known recipe (zero base ingredients), `results` was never defined, and line 208 `for result in results:` raised `NameError`. This crashed anytime a user logged only complex dishes that all have recipes in the DB.
- **Fix Detail:** Added `results = []` before the `if base_tasks:` block. When `base_tasks` is empty, the for-loop safely iterates zero times. Verified with `tests/ISSUE_NAMEERROR_unit_recipe.py`.

### `httpx.AsyncClient` never closed in FoodbankService
- **Files:** `app/services/foodbank.py:22-24`
- **Issue Detail:** `self.http_client = httpx.AsyncClient(...)` is created in `__init__` but never closed. No `close()` method, no `__del__`, no async context manager. The client persists for the lifetime of the process, leaking connections and potentially hitting OS file-descriptor limits under sustained load.
- **Fix Plan:** Add `async def close(self)` that calls `await self.http_client.aclose()`. Call it in `api.py` lifespan shutdown handler (`yield` → `await foodbank_service.http_client.aclose()`).

### `seed_db` bare `INSERT OR REPLACE` into FTS5
- **Files:** `app/services/foodbank.py:400-418`
- **Issue Detail:** `seed_db` uses `INSERT OR REPLACE INTO foods VALUES (...)` without a rowid subquery. In FTS5, this creates duplicate records instead of replacing. The proper pattern (used in `upsert_food` at lines 149-152) is `INSERT OR REPLACE INTO foods (rowid, ...) VALUES ((SELECT rowid FROM foods WHERE name = ?), ...)`. The `seed_db` method bypasses this, risking duplicate rows in tests.
- **Fix Plan:** Refactor `seed_db` to call `upsert_food` in a loop, or add the rowid subquery to its INSERT statement.

### Frontend creates new `AsyncClient` per request
- **Files:** `app/frontend.py:12-22`
- **Issue Detail:** Each `async_get`, `async_post`, and `async_delete` creates a new `httpx.AsyncClient(timeout=30.0)` inside an `async with` block. This means every API call from the frontend (summary, meals, log, clear, goals) creates a fresh TCP connection pool. The backend had this same issue and was fixed — the frontend was missed.
- **Fix Plan:** Create a single module-level `_client = httpx.AsyncClient(timeout=30.0)` and reuse it across all three helper functions.

### `upsert_food` hardcodes `is_complete_protein=0`
- **Files:** `app/services/foodbank.py:146-155`
- **Issue Detail:** `upsert_food` method signature doesn't accept `is_complete_protein` and hardcodes it to `0`. This means the DB can never store complete protein data (e.g., chicken breast, fish, paneer are complete proteins). The `foods` FTS5 table has the column and `_init_foodbank` seeds it correctly (e.g., `Paneer` has `1`), but any runtime upsert silently overwrites it to `0`.
- **Fix Plan:** Add `is_complete_protein: int = 0` parameter to `upsert_food` and pass it through from callers (`find_source_of_truth`, `_get_nutrition_data_core`, etc.).

### Duplicate seed data in two locations
- **Files:** `app/services/database.py:93-107`, `app/services/foodbank.py:402-416`
- **Issue Detail:** The identical 12-food seed list is defined in both `DatabaseManager._init_foodbank()` and `FoodbankService.seed_db()`. Any change to the seed data (new foods, corrected macros) must be applied in two places. Already diverged slightly — `_init_foodbank` uses `INSERT INTO` while `seed_db` uses `INSERT OR REPLACE INTO`.
- **Fix Plan:** Extract the seed data into a module-level constant (e.g., `DEFAULT_FOODS` in `database.py`) and import it in both locations.

### `FoodLogSchema.md` wiki page out of sync
- **Files:** `wiki/logic/FoodLogSchema.md`
- **Issue Detail:** The wiki schema is missing two things present in the actual code (`app/schemas/food_schemas.py:16-22`):
  1. `FoodItem.verified: bool = False` field
  2. `GoalRequest(BaseModel)` class
  The wiki shows the schema as it was before the verified column was added.
- **Fix Plan:** Update `wiki/logic/FoodLogSchema.md` to include the `verified` field and the `GoalRequest` model.

### No `AsyncClient` cleanup on app shutdown
- **Files:** `app/api.py:24-28`
- **Issue Detail:** The FastAPI `lifespan` handler cancels the heartbeat task on shutdown but never closes `foodbank_service.http_client`. Combined with issue #4, the client's connections are left dangling when the server stops.
- **Fix Plan:** After `task.cancel()`, add `await foodbank_service.http_client.aclose()`. This requires `foodbank_service` to expose a close method (see fix plan for issue #4).

### Duplicated Code in Meal Logging
- **Files:** `app/api.py`
- **Issue Detail:** The `log_meal` and `log_vision_meal` endpoints in `app/api.py` contain nearly identical code for calculating total sub-macros and inserting meal data into the database. This violates the DRY (Don't Repeat Yourself) principle, making the code harder to maintain and increasing the risk of introducing inconsistencies.
- **Fix Plan:** Refactor the duplicated logic into a private helper function. This function will take the meal data (items, totals, meal_type, etc.) as arguments and handle the database insertion, promoting code reuse and simplifying the endpoint logic.

### Nutritional Resolution Silent Failures
- **Files:** `app/services/foodbank.py`, `app/services/extraction.py`
- **Issue Detail:** Items successfully extracted from text/image often end up with 0 calories because all resolution paths (Local DB $\rightarrow$ Web Search $\rightarrow$ Internal Estimate) return `None` or `error`. The system currently keeps the item but fails to provide nutritional value.
- **Fix Plan:** Implement a tiered fallback system. If all specific lookups fail, attempt a "category-based" estimate (e.g. "generic snack" or "generic meal") to avoid absolute zeros.

### Fragile Internal Nutrition Estimates
- **Files:** `prompts/prompts.yaml`, `app/services/foodbank.py`
- **Issue Detail:** The `internal_estimate` prompt is overly restrictive or fails to handle regional names, often returning `{'error': 'unknown'}` for valid foods.
- **Fix Plan:** Refine the `internal_estimate` prompt to be more permissive with regional cuisines and provide a structured "best guess" instead of a hard error when high confidence is not possible.

### Web Search Precision for Regional Foods
- **Files:** `prompts/prompts.yaml`, `app/services/foodbank.py`
- **Issue Detail:** DuckDuckGo searches for regional dishes (e.g. "Misal Pav") often return generic results or blogs rather than authoritative nutrition facts per 100g.
- **Fix Plan:** Update `NUTRITION_FACTS_QUERY` and `web_search` prompts to explicitly request "nutrition facts per 100g" and "authoritative data sources" to minimize generic noise.

### Complex and Inefficient Database Calls in FoodbankService
- **Files:** `app/services/foodbank.py`, `app/services/database.py`
- **Issue Detail:** Excessive `asyncio.to_thread` calls for micro-queries created significant scheduling overhead, especially during the resolution pipeline and verification queue processing.
- **Fix Detail:** 
    1. Implemented `_local_resolution_sync` in `FoodbankService` to group Exact Search $\rightarrow$ Fuzzy Match $\rightarrow$ Final Match into a single thread switch.
    2. Refactored `process_verification_queue` to batch-delete stale items and batch-increment retries using a new `run_foodbank_batch` (executemany) method in `DatabaseManager`.
    3. Updated `seed_db` to use batch insertions.
    4. Reduced thread-switch frequency in the resolution pipeline from 3+ to 1 per item.

### Redundant Web Searches in FoodbankService
- **Files:** `app/services/foodbank.py`
- **Issue Detail:** The `search_web_for_food` and `find_source_of_truth` methods both fetch web pages, sometimes for the same query. The `_get_nutrition_data_core` function attempts to mitigate this by fetching HTML once, but the overall logic remains complex and prone to redundant network requests.
- **Fix Plan:** Create a single, streamlined function responsible for fetching web page content. This function will cache results for a short period to avoid re-fetching the same URL within the same request. Other functions will then use this helper to get HTML content, ensuring that each page is fetched only once.

### Inefficient Database Seeding
- **Files:** `app/services/foodbank.py`
- **Issue Detail:** The `seed_db` function, used for seeding the database in tests, iterates through `DEFAULT_FOODS` and calls `upsert_food` for each item. This results in multiple individual database transactions, which is inefficient for bulk data insertion.
- **Fix Plan:** Modify the `DatabaseManager` to include a bulk seeding method that uses `executemany` to insert all default food items in a single transaction. This will significantly speed up the database seeding process.

### Hardcoded SQL and Search Queries
- **Files:** `app/api.py`, `app/services/foodbank.py`
- **Issue Detail:** SQL queries and web search queries are hardcoded directly within the application's business logic. This makes the code harder to read, maintain, and adapt to different database systems or search providers in the future.
- **Fix Plan:** Externalize all SQL queries and search query templates into a dedicated constants file or a configuration file (e.g., `app/core/queries.py`). This will centralize the queries, making them easier to manage and modify.

### Inconsistent Logging and Error Handling
- **Files:** `app/api.py`, `app/services/extraction.py`, `app/services/foodbank.py`
- **Issue Detail:** The codebase uses `print()` statements for debugging and logging, which is not a scalable or manageable approach. Additionally, error handling is inconsistent across different modules, with varying HTTP status codes and error message formats.
- **Fix Plan:** Implement a standardized logging framework using Python's `logging` module. Configure formatters and handlers to stream logs to the console or a file. Standardize error handling by creating a set of custom exception classes and a middleware or decorator to catch them and return consistent JSON error responses.

### No Pydantic validation for Onboarding LLM output
- **Files:** `app/services/onboarding.py`, `app/api.py`, `app/schemas/food_schemas.py`
- **Issue Detail:** The `OnboardingService` previously used `.get()` with defaults if LLM parsing failed, leading to inaccurate baseline calculations without warning.
- **Fix Detail:** 
    1. Implemented `OnboardingAttributes.model_validate_json()` in `OnboardingService` to enforce a strict data contract.
    2. Introduced `OnboardingValidationError` to capture and transport detailed Pydantic validation errors.
    3. Updated the `/onboard` API endpoint to catch `OnboardingValidationError` and return an `HTTP 422 Unprocessable Entity` with a breakdown of missing/invalid fields.
    4. Updated unit tests to verify both successful parsing and explicit validation failures.


### Nutritional Resolution Silent Failures
- **Files:** `app/services/foodbank.py`, `app/services/extraction.py`
- **Issue Detail:** Items successfully extracted from text/image often end up with 0 calories because all resolution paths (Local DB $\rightarrow$ Web Search $\rightarrow$ Internal Estimate) return `None` or `error`. The system currently keeps the item but fails to provide nutritional value.
- **Fix Plan:** Implement a tiered fallback system. If all specific lookups fail, attempt a "category-based" estimate (e.g. "generic snack" or "generic meal") to avoid absolute zeros.

### Fragile Internal Nutrition Estimates
- **Files:** `prompts/prompts.yaml`, `app/services/foodbank.py`
- **Issue Detail:** The `internal_estimate` prompt is overly restrictive or fails to handle regional names, often returning `{'error': 'unknown'}` for valid foods.
- **Fix Plan:** Refine the `internal_estimate` prompt to be more permissive with regional cuisines and provide a structured "best guess" instead of a hard error when high confidence is not possible.

### Web Search Precision for Regional Foods
- **Files:** `prompts/prompts.yaml`, `app/services/foodbank.py`
- **Issue Detail:** DuckDuckGo searches for regional dishes (e.g. "Misal Pav") often return generic results or blogs rather than authoritative nutrition facts per 100g.
- **Fix Plan:** Update `NUTRITION_FACTS_QUERY` and `web_search` prompts to explicitly request "nutrition facts per 100g" and "authoritative data sources" to minimize generic noise.


### Vision Client connection overhead
- **Files:** `app/utils/vision_client.py`
- **Issue Detail:** `send_vision_log` uses `httpx.post()` directly. This creates a new connection pool for every single image upload, increasing latency and resource usage.
- **Fix Plan:** Implement a shared `httpx.Client` in `vision_client.py` to reuse TCP connections.

### Audit Logic historical duplication
- **Files:** `wiki/logic/audit_logic.md`
- **Issue Detail:** `audit_logic.md` contains a detailed "to-do" list for fixes (Phase 1-4) that have already been implemented and marked as [FIXED] in the main `audit_logs.md`. This creates redundancy and confusion about the current state of the codebase.
- **Fix Plan:** Archive or remove the "to-do" steps from `audit_logic.md` once they are verified in the main audit logs.

### Medical Firewall Bypass
- **Files:** `app/services/planner.py`, `prompts/prompts.yaml`
- **Issue Detail:** The LLM was ignoring medical boundaries and acknowledging instructions instead of acting on them.
- **Fix Detail:** Implemented system role messages in `PlannerService` and reorganized the `meal_copilot` prompt to place the User Query at the end. Verified that queries about acute pain or prescriptions now correctly trigger the medical disclaimer and halt meal planning.

### Extraction Crash on Empty Input
- **Files:** `app/services/extraction.py`
- **Issue Detail:** Calling `parse("")` crashed with a `ValueError`.
- **Fix Detail:** Updated `_resolve_and_build_log` to return an empty `FoodLog` instead of raising an exception.

### Missing Voice Correction in Extraction
- **Files:** `app/services/extraction.py`, `prompts/prompts.yaml`
- **Issue Detail:** `is_voice` parameter in `extract_items` was ignored, preventing phonetic normalization.
- **Fix Detail:** Integrated the `voice_correction` prompt when `is_voice=True`, enabling phonetic normalization (e.g., "better garlic can't" $\rightarrow$ "Butter garlic").

### Planner Service Architecture
- **Files:** `app/services/planner.py`
- **Issue Detail:** Need to verify the Router $\rightarrow$ Knowledge Loader $\rightarrow$ Copilot flow and ensure system stability during router failures.
- **Fix Detail:** Implemented and verified the full routing pipeline. Added safety fallbacks to ensure the system remains functional even if the router fails.


