# Architecture

## Stack

FastAPI + Streamlit + SQLite (FTS5) + LiteLLM (ollama/gemma4:e2b) + httpx + Pydantic

## Component Map

```
app/
  api.py              FastAPI: POST /log, POST /vision-log, GET /summary (daily + weekly), /meals, /pending-count, /sync-status, POST /verify-queue, POST /goals, DELETE /clear. Lifespan manages heartbeat and closes FoodbankService.
  frontend.py         Streamlit: daily progress, static calendar week buffer, food journal, meal logging, goal settings. Uses shared httpx.AsyncClient for pooling.
  core/config.py      Config: LITELLM_API_BASE, LLM_MODEL, DB paths, prompts path
  schemas/food_schemas.py  Pydantic: Macros, SubMacros, FoodItem, FoodLog, GoalRequest
  services/
     database.py       DatabaseManager: 2 SQLite DBs (foodbank.db + macros.db).
                       FTS5 foods table, recipes, pending_verification, sync_status, meals.
                       Defines DEFAULT_FOODS for consistent seeding.
                        Implements weekly summary aggregation (static calendar week).
     foodbank.py       FoodbankService: Consolidated nutrition resolution logic. Implements L1 in-memory caching to bypass DB/Web latency. Handles DB lookups, web search, offline estimates, and verification queue. Provides close() for resource cleanup.
     extraction.py     ExtractionService: Two-pass LLM extraction + Unified Resolution Engine (_resolve_and_build_log) for both text and vision paths. Vision pipeline handles multimodal payload (text + image + optional hint) for Home/Wild estimation.
     onboarding.py     OnboardingService: PCOS baseline macro calibration from user bio text.


prompts/prompts.yaml  Externalized LLM prompts (extraction.main/verification/vision_estimate, foodbank.web_search/internal_estimate, planner.empathetic_suggestion)
  tests/                pytest suites
  debug/                non-pytest diagnostic scripts
  scripts/ingest_csv.py CSV->foodbank importer
raw/                  Cloud-generated logic specs
wiki/                 QA rules, logic docs, agent index
```

## Data Flow

```
Onboarding Flow:
User Bio Text -> OnboardingService.calculate_pcos_baseline()
  -> LLM Extraction (onboarding_parse prompt) -> {height, weight, activity, goal}
  -> Math: BMR (Mifflin-St Jeor) -> TDEE -> Goal Modifier -> PCOS Penalty (0.85x) -> Macro Split (40/35/25)
  -> Persist to macros.db (goals table)

Food Logging Flow:
User Text -> ExtractionService.parse()
  1. LLM extraction (prompts.yaml extraction.main)
  2. Verification Guardrail (extraction.verification) -> detect missed items
  3. Deduplication (remove junk terms, overlapping names)
  4. For each item:
     a. Recipe check -> if known recipe, expand into base ingredients (parallel asyncio.gather)
     b. Base ingredient -> get_nutrition_data():
        - L1 Cache lookup (In-memory dictionary)
        - DB lookup (FTS5 exact + fuzzy)
        - [OFFLINE] cached data or LLM estimate (verified=0, queued)
        - [ONLINE] find_source_of_truth -> search_web_for_food -> internal_estimate
        - Standardized flat macro return for all paths
        - Atwater guardrail (cal = P*4 + C*4 + F*9, correct if >20% deviation)
C. Unified Resolution Convergence:
   Both Text and Vision paths converge into `_resolve_and_build_log()`:
     1. Input: [{name, grams}] list + meal_id
     2. Parallel Resolution: Recipe check -> Base ingredient lookup (Parallel asyncio.gather)
     3. Build FoodLog: Aggregates items, total_macros, total_calories
     4. Returns standardized `FoodLog` object
```
User Text -> ExtractionService.parse()
  1. LLM extraction (prompts.yaml extraction.main)
  2. Verification Guardrail (extraction.verification) -> detect missed items
  3. Deduplication (remove junk terms, overlapping names)
  4. For each item:
     a. Recipe check -> if known recipe, expand into base ingredients (parallel asyncio.gather)
     b. Base ingredient -> get_nutrition_data():
        - L1 Cache lookup (In-memory dictionary)
        - DB lookup (FTS5 exact + fuzzy)
        - [OFFLINE] cached data or LLM estimate (verified=0, queued)
        - [ONLINE] find_source_of_truth -> search_web_for_food -> internal_estimate
        - Standardized flat macro return for all paths
        - Atwater guardrail (cal = P*4 + C*4 + F*9, correct if >20% deviation)
C. Unified Resolution Convergence:
   Both Text and Vision paths converge into `_resolve_and_build_log()`:
     1. Input: [{name, grams}] list + meal_id
     2. Parallel Resolution: Recipe check -> Base ingredient lookup (Parallel asyncio.gather)
     3. Build FoodLog: Aggregates items, total_macros, total_calories
     4. Returns standardized `FoodLog` object


Vision Pipeline (POST /vision-log):
   User Image (base64 + environment + optional hint) -> ExtractionService.extract_from_image()
      1. Multimodal payload: text (vision_estimate prompt + hint) + image (base64) $\rightarrow$ gemma4:e2b (Two-step Analysis $\rightarrow$ Extraction)
     2. Environment rules: Home (~250-500g plates) vs. Wild (~300-600g plates)
     3. Returns [{name, grams}] items
     4. Pass to Unified Resolver -> build FoodLog
     5. Persist to macros.db (meal_type="Vision")


Heartbeat (asyncio task, lifespan-managed):
  Every 60s: check network -> process verification queue -> update sync timestamp
```

## Databases

### foodbank.db
- `foods` (FTS5 virtual table): name, aliases, calories, protein, carbs, fat, fiber, sugar, saturated_fat, unsaturated_fat, is_complete_protein, verified, source
- `recipes`: dish_name (PK), recipe_json
- `pending_verification`: name (PK), retry_count
- `sync_status`: id (PK), last_sync

### macros.db
- `meals`: id, meal_id, timestamp, items_json, total_protein/carbs/fat/cals/fiber/sugar/saturated_fat/unsaturated_fat, meal_type
- `goals`: id (PK), protein, carbs, fat, calories

## Key Design Decisions

- **Async**: All DB operations via `asyncio.to_thread`; all LLM calls via `litellm.acompletion`; shared `httpx.AsyncClient` for connection pooling
- **Two-pass extraction**: 1st pass extracts items, 2nd pass (verification guardrail) catches missed items
- **Recipe expansion**: Known dishes decomposed into base ingredients before macro calculation (anti-hallucination)
- **Offline-first**: DB cached data returned immediately when offline; unverified items queued for later sync
- **Atwater guardrail**: LLM calorie estimates validated against macro-derived calories
- **L1 Cache**: In-memory lookup for frequent food items to eliminate redundant DB/network roundtrips
- **PCOS Calibration**: Deterministic BMR/TDEE calculation with a 15% metabolic penalty to provide clinically relevant targets for insulin-resistant profiles
