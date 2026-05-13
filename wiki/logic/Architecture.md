# Architecture

## Stack

FastAPI + Streamlit + SQLite (FTS5) + LiteLLM (ollama/gemma4:e2b) + httpx + Pydantic

## Component Map

```
app/
  api.py              FastAPI: POST /log, POST /vision-log, GET /summary (daily + weekly), /meals, /pending-count, /sync-status, POST /verify-queue, POST /goals, DELETE /clear. Lifespan manages heartbeat and closes FoodbankService.
  frontend.py         Streamlit: daily progress, 7-day rolling buffer, food journal, meal logging, goal settings. Uses shared httpx.AsyncClient for pooling.
  core/config.py      Config: LITELLM_API_BASE, LLM_MODEL, DB paths, prompts path
  schemas/food_schemas.py  Pydantic: Macros, SubMacros, FoodItem, FoodLog
  services/
     database.py       DatabaseManager: 2 SQLite DBs (foodbank.db + macros.db).
                      FTS5 foods table, recipes, pending_verification, sync_status, meals.
                      Defines DEFAULT_FOODS for consistent seeding.
                      Implements weekly summary aggregation (last 7 days).
    foodbank.py       FoodbankService: Consolidated nutrition resolution logic. Implements L1 in-memory caching to bypass DB/Web latency. Handles DB lookups, web search, offline estimates, and verification queue. Provides close() for resource cleanup.
    extraction.py     ExtractionService: Two-pass LLM extraction + async nutrition resolution + vision pipeline (extract_from_image using multimodal payload for Home/Wild estimation).
prompts/prompts.yaml  Externalized LLM prompts (extraction.main/verification/vision_estimate, foodbank.web_search/internal_estimate, planner.empathetic_suggestion)
  tests/                pytest suites
  debug/                non-pytest diagnostic scripts
  scripts/ingest_csv.py CSV->foodbank importer
raw/                  Cloud-generated logic specs
wiki/                 QA rules, logic docs, agent index
```

## Data Flow

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
  5. Aggregate results, return FoodLog with total_macros + total_calories
  6. Persist to macros.db (meals table)

Vision Pipeline (POST /vision-log):
  User Image (base64 + environment) -> ExtractionService.extract_from_image()
    1. Multimodal payload: text (vision_estimate prompt) + image (base64) -> gemma4:e2b
    2. Environment rules: Home (~250-500g plates) vs. Wild (~300-600g plates)
    3. Returns [{name, grams}] items
    4. Async resolve nutrition per item via _get_nutrition_for_ingredient()
    5. Build FoodLog, persist to macros.db (meal_type="Vision")

Heartbeat (asyncio task, lifespan-managed):
  Every 60s: check network -> process verification queue -> update sync timestamp
```

## Databases

### foodbank.db
- `foods` (FTS5 virtual table): name, aliases, calories, protein, carbs, fat, fiber, is_complete_protein, verified
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
