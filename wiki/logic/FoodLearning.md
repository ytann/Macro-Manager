# Food Identification & Learning Logic

Resolved by `app/services/foodbank.py` and `app/services/extraction.py`.

## 1. Identification Flow
 
For every item extracted from the user's log:
 
1. **L1 Cache Lookup**: Immediate check of in-memory cache for normalized name.
2. **Canonicalization Layer**: If no exact hit, perform fuzzy matching (Levenshtein) against the database to map typos/variations to existing entries.
3. **DB Lookup**: Search `foodbank.db` via FTS5. If item is found and `verified=1`, return immediately.
3. **Network Check**: `_is_network_available()` (HEAD to `https://1.1.1.1`) determines online/offline path.
4. **Offline Path**: Return DB-cached data if available. Queue unverified items (`verified=0`) for future verification. If no cache, use `internal_estimate` (LLM guess), persist with `verified=0`.
5. **Online Path (Source of Truth Flow)**: 
    - DB verified data (`verified=1`) -> return immediately
    - **Authoritative Search**: `find_source_of_truth()` uses Tavily API search results $\rightarrow$ LLM validates against high-confidence sources $\rightarrow$ marks `verified=1` if confidence is High/Medium.
    - `search_web_for_food()` -> general web search with fallback queries
    - `internal_estimate()` -> LLM "Expert Estimator" using Ingredient-Based Inference as last resort.
    - **Category Fallback**: If all above return `None` or `error`, a tiered category-based estimate (e.g., "generic grain", "generic vegetable") is applied to avoid 0-calorie silent failures.
    All methods return a uniform flat dictionary containing macros.
 
## 2. Verified Column Logic
 
The `verified` column in the `foods` table distinguishes between estimated and confirmed data:
- `verified=1`: Data confirmed via authoritative web search (Source of Truth flow).
- `verified=0`: Data derived from local LLM estimates or cached items awaiting verification.
- **Promotion**: Items are promoted from `0` -> `1` only after successful heartbeat sync or manual verification.

## 2. Unified Resolution & Recipe Expansion

Both Text and Vision paths converge into `ExtractionService._resolve_and_build_log()` to ensure consistent processing:

1. Fetch recipe JSON from `recipes` table for any item recognized as a complex dish
2. Scale ingredient weights by `grams / total_recipe_weight`
3. Resolve all recipe ingredients and base ingredients in parallel via `asyncio.gather` (throttled by global LLM semaphore for stability)
4. Create dish summary `FoodItem(name="Dish (Total)", ...)` + ingredient breakdown
5. Aggregate all results into a standardized `FoodLog` object

## 3. Verification Queue
 
Foods learned offline or from low-confidence estimates are queued in `pending_verification`:
 
- Heartbeat (60s) processes queue when network available
- `POST /verify-queue` for manual trigger
- Max 5 retries per item; stale items auto-removed
- Successfully verified items upserted with `verified=1`
- **Seeding**: `seed_db()` ensures initial data is persisted using `upsert_food` to avoid FTS5 record duplication


## 4. Anti-Hallucination Measures

- **Recipe verification**: Recipe generation + cross-verification pass (in prompts)
- **Atwater guardrail**: If LLM calories deviate >20% from `P*4 + C*4 + F*9`, use derived value
- **Source of Truth**: Authoritative web search prioritizes government/established sources
- **Confidence tiers**: High/Medium -> `verified=1`, Low -> `verified=0` + queued
- **Temperature=0.0**: Deterministic extraction outputs