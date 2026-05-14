# QA Failure Rules

## Code Hygiene
1. No backticks in .py files
2. Always use local Ollama port 11434
3. AI NEVER guesses macros; Python fetches from DB
4. Data Types: CSV imports must cast to float before DB insertion

## Extraction Resilience
5. Parsers must be shape-agnostic (check 'items', 'ingredients', 'data', 'response') — fail gracefully on missing data
6. Two-pass extraction: verification guardrail catches missed items
7. Identification Flakiness: items without explicit quantifiers handled by shape-agnostic parsing + verification pass
8. Use `.get()` for dictionary values instead of iterating keys to prevent unpacking errors

## DB & Persistence
9. DB Queries: Use `date('now')` for daily totals to avoid timezone/format mismatches
10. `CREATE VIRTUAL TABLE IF NOT EXISTS` — never DROP TABLE on startup (destroys learned data)
11. Seed initial foods only when table has 0 rows
12. FTS5 `DELETE FROM foods WHERE name = ?` works for content-less FTS5 tables (supported in FTS5)

## Sync & Offline
13. `update_sync_timestamp()` only when items actually processed (not on empty queue runs)
14. `POST /verify-queue` must trigger `run_sync_cycle()` (wraps process + timestamp update)
15. Offline path must queue unverified DB-cached items for later sync
16. Retry limit (5) on `pending_verification` to prevent infinite LLM calls on fake items

## Complex Dishes & Hallucinations
17. Complex dishes must be expanded into base ingredients before macro calculation
18. Recipe generation: Reasoning -> Generation -> Verification loop
19. Atwater guardrail: `cal = P*4 + C*4 + F*9`, correct if >20% deviation
20. Temperature = 0.0 for deterministic outputs

## Concurrency & Safety
21. `asyncio.gather` — tasks must return values, not mutate shared state (non-atomic)
22. SQLite `check_same_thread=False` for concurrent heartbeat + API access
23. `float(val or 0)` for all LLM-returned numeric fields (null safety)

## Knowledge Gap Handling
24. Missing food -> fetch 100g macros from LLM/web, persist via `upsert_food`
25. Volume estimation must be food-aware (density-based, not static ranges)
26. Low-confidence data marked `verified=0` and queued for SoT verification
27. Onboarding extraction must return strict JSON; fallback defaults must be logged to avoid silent miscalibration