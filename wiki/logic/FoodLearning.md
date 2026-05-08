# Food Identification & Learning Logic

Resolved by `app/services/foodbank.py` and `app/services/extraction.py`.

## 1. Identification Flow

For every item extracted from the user's log:

1. **DB Lookup**: Search `foodbank.db` via FTS5 — exact name match, alias match (`aliases LIKE`), then FTS5 MATCH query with `*` suffix on individual words.
2. **Network Check**: `_is_network_available()` (HEAD to `https://1.1.1.1`) determines online/offline path.
3. **Offline Path**: Return DB-cached data if available. Queue unverified items (`verified=0`) for future verification. If no cache, use `internal_estimate` (LLM guess), persist with `verified=0`.
4. **Online Path**: 
   - DB verified data (`verified=1`) -> return immediately
    - `find_source_of_truth()` -> authoritative web extraction (DuckDuckGo HTML -> LLM validation)
    - `search_web_for_food()` -> general web search with fallback queries
    - `internal_estimate()` -> LLM estimate as last resort
    All methods return a uniform flat dictionary containing macros.

## 2. Recipe Expansion

`ExtractionService.parse()` checks `self.foodbank.get_recipe(name)` before treating an item as a base ingredient:

1. Fetch recipe JSON from `recipes` table
2. Scale ingredient weights by `grams / total_recipe_weight`
3. Resolve all recipe ingredients in parallel via `asyncio.gather`
4. Create dish summary `FoodItem(name="Dish (Total)", ...)` + ingredient breakdown

## 3. Verification Queue

Foods learned offline or from low-confidence estimates are queued in `pending_verification`:

- Heartbeat (60s) processes queue when network available
- `POST /verify-queue` for manual trigger
- Max 5 retries per item; stale items auto-removed
- Successfully verified items upserted with `verified=1`

## 4. Anti-Hallucination Measures

- **Recipe verification**: Recipe generation + cross-verification pass (in prompts)
- **Atwater guardrail**: If LLM calories deviate >20% from `P*4 + C*4 + F*9`, use derived value
- **Source of Truth**: Authoritative web search prioritizes government/established sources
- **Confidence tiers**: High/Medium -> `verified=1`, Low -> `verified=0` + queued
- **Temperature=0.0**: Deterministic extraction outputs