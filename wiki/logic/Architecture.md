# Architecture

## Stack

FastAPI + Streamlit + SQLite (FTS5) + LiteLLM (ollama/llama3.1:latest) + httpx + Pydantic

## Component Map

```
app/
  api.py              FastAPI: POST /log, GET /summary, /meals, /pending-count, /sync-status, POST /verify-queue, DELETE /clear
  frontend.py         Streamlit: daily progress, food journal, meal logging
  core/config.py      Config: LITELLM_API_BASE, LLM_MODEL, DB paths, prompts path
  schemas/food_schemas.py  Pydantic: Macros, SubMacros, FoodItem, FoodLog
  services/
    database.py       DatabaseManager (Singleton): 2 SQLite DBs (foodbank.db + macros.db).
                      FTS5 foods table, recipes, pending_verification, sync_status, meals.
    foodbank.py       FoodbankService: DB lookups, web search, offline estimates, verification queue.
    extraction.py     ExtractionService: Two-pass LLM extraction + async nutrition resolution.
prompts/prompts.yaml  Externalized LLM prompts (extraction.main/verification, foodbank.web_search/internal_estimate)
tests/                pytest + debug scripts
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
        - DB lookup (FTS5 exact + fuzzy)
        - [OFFLINE] cached data or LLM estimate (verified=0, queued)
        - [ONLINE] find_source_of_truth -> search_web_for_food -> internal_estimate
        - Atwater guardrail (cal = P*4 + C*4 + F*9, correct if >20% deviation)
  5. Aggregate results, return FoodLog with total_macros + total_calories
  6. Persist to macros.db (meals table)

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

## Key Design Decisions

- **Async**: All DB operations via `asyncio.to_thread`; all LLM calls via `litellm.acompletion`; shared `httpx.AsyncClient` for connection pooling
- **Two-pass extraction**: 1st pass extracts items, 2nd pass (verification guardrail) catches missed items
- **Recipe expansion**: Known dishes decomposed into base ingredients before macro calculation (anti-hallucination)
- **Offline-first**: DB cached data returned immediately when offline; unverified items queued for later sync
- **Atwater guardrail**: LLM calorie estimates validated against macro-derived calories
- **Per-request caching**: `self.foodbank_cache` avoids duplicate lookups for same ingredient within one parse call