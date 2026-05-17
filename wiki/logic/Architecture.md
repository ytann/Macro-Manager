# Architecture

## Stack

FastAPI + Streamlit + SQLite (FTS5) + LiteLLM (ollama/gemma4:e2b) + httpx + Pydantic

## Component Map

```
app/
  api.py              FastAPI: POST /log/start, GET /log/status/{id}, POST /log, POST /vision-log, GET /summary (daily + weekly), /meals, /pending-count, /sync-status, POST /verify-queue, POST /goals, DELETE /clear, POST /planner. Lifespan manages heartbeat and closes FoodbankService.
  frontend.py         Streamlit: daily progress, static calendar week buffer, food journal, meal logging, goal settings, Clinical Copilot UI. Uses shared httpx.AsyncClient for pooling.
  core/config.py      Config: LITELLM_API_BASE, LLM_MODEL, DB paths, prompts path
  core/llm.py            LLM Utility: Global concurrency control (Semaphore) for Ollama stability
  schemas/food_schemas.py  Pydantic: Macros, SubMacros, FoodItem, FoodLog, GoalRequest
  services/
       database.py       DatabaseManager: 2 SQLite DBs (foodbank.db + macros.db).
                        FTS5 foods table, recipes, pending_verification, sync_status, meals.
                        Defines DEFAULT_FOODS for consistent seeding.
                        Implements weekly summary aggregation (static calendar week).
                        Provides `run_foodbank()` and `run_macros()` helpers for efficient thread-safe execution.
       foodbank.py       FoodbankService: Consolidated nutrition resolution logic. Implements Normalization Engine (normalize_and_upsert) for Per 100g consistency, Canonicalization Layer (fuzzy matching) and L1 in-memory caching. Handles DB lookups, web search, offline estimates, and verification queue. Provides close() for resource cleanup.
        extraction.py     ExtractionService: Decoupled async pipeline (Item Extraction -> Background Resolution). Unified Resolution Engine (_resolve_and_build_log). Vision Hub manages three paths: Volumetric AI (physics-based), Label OCR (package scanning), and QR/Barcode (OpenFoodFacts + LLM fallback).
       onboarding.py     OnboardingService: PMOS baseline macro calibration from user bio text using Pydantic validation for extracted attributes.
       planner.py         PlannerService: Clinical Copilot orchestration. Implements Router -> Knowledge -> Copilot flow with a Medical Firewall to prevent AI medical diagnosis.



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
User Bio Text -> OnboardingService.calculate_pmos_baseline()
  -> LLM Extraction (onboarding_parse prompt) -> {height, weight, activity, goal}
  -> Math: BMR (Mifflin-St Jeor) -> TDEE -> Goal Modifier -> PMOS Penalty (0.85x) -> Macro Split (40/35/25)
  -> Persist to macros.db (goals table)

Food Logging Flow:
User Text -> ExtractionService.extract_items()
  1. Fast LLM extraction (prompts.yaml extraction.main)
  2. Returns {items, meal_id} immediately to UI
  3. Triggers Background Resolution via FastAPI BackgroundTasks:
     a. For each item:
        - Recipe check -> expand into base ingredients (parallel asyncio.gather)
        - Base ingredient -> get_nutrition_data():
           - L1 Cache lookup
           - Canonicalization Layer (Fuzzy match against DB)
           - DB lookup (FTS5)
           - [OFFLINE] cached data or LLM estimate (verified=0, queued)
           - [ONLINE] Authoritative web search -> General search -> LLM Expert Estimate -> Category Fallback (prevents 0-cal failures)
           - Standardized flat macro return for all paths
     b. Atwater guardrail (cal = P*4 + C*4 + F*9, correct if >20% deviation)
     c. Persist to macros.db
  4. UI polls GET /log/status/{meal_id} to update progress spinners.

Clinical Copilot Flow:
User Query -> PlannerService.plan()
  1. Router analyzes intent (General vs. Specific vs. Medical)
  2. Knowledge Loader fetches relevant PMOS guidelines from wiki
  3. Clinical Copilot generates empathetic plan (meal_copilot prompt)
  4. Medical Firewall validates output (Halt and refer if acute symptoms/prescriptions detected)
  5. Returns tailored plan + legal disclaimer to UI


Vision Hub (POST /vision-log):
    User Image (base64 + mode + optional hint) -> ExtractionService.extract_from_image()
       1. Mode Selection:
          a. Photo (Volumetric): Multimodal payload -> Gemma 4 (Container Geometry -> Fill % -> Volume * Density = Mass)
          b. Label Scan: OCR extraction -> Gemma 4 (Parse Nutrition Facts Table -> Macros)
          c. QR/Barcode: Barcode Decoder -> OpenFoodFacts API -> Verified Macros (Fallback: Gemma 4 Vision reads barcode digits -> Tavily Search)
       2. Returns [{name, grams}] items
       3. Pass to Unified Resolver -> build FoodLog
       4. Persist to macros.db (meal_type="Vision")


Heartbeat (asyncio task, lifespan-managed):
  Every 60s: check network -> process verification queue -> update sync timestamp
```

## Databases

### foodbank.db
- `foods` (FTS5 virtual table): name, aliases, reported_qty, reported_p, reported_c, reported_f, p_per_100, c_per_100, f_per_100, reported_cal, cal_per_100, reported_fiber, fiber_per_100, sugar, saturated_fat, unsaturated_fat, is_complete_protein, verified, source
- `recipes`: dish_name (PK), recipe_json
- `pending_verification`: name (PK), retry_count
- `sync_status`: id (PK), last_sync

### macros.db
- `meals`: id, meal_id, timestamp, items_json, total_protein/carbs/fat/cals/fiber/sugar/saturated_fat/unsaturated_fat, meal_type
- `goals`: id (PK), protein, carbs, fat, calories

## Key Design Decisions

- **Async**: All DB operations via `asyncio.to_thread`; all LLM calls routed through `safe_acompletion` (global semaphore) to prevent Ollama saturation; shared `httpx.AsyncClient` for connection pooling
- **Async Pipeline**: Decoupled extraction and resolution. Returns extracted items instantly and resolves nutrition as a background task to eliminate UI hang.
- **Canonicalization Layer**: Use of Levenshtein-based fuzzy matching to map item variations to DB entries, reducing slow web search triggers.
- **Self-Verifying Extraction**: High-recall single-pass LLM extraction to maximize recall while minimizing API latency
- **Recipe expansion**: Known dishes decomposed into base ingredients before macro calculation (anti-hallucination)
- **Offline-first**: DB cached data returned immediately when offline; unverified items queued for later sync
- **Atwater guardrail**: LLM calorie estimates validated against macro-derived calories
- **L1 Cache**: In-memory lookup for frequent food items to eliminate redundant DB/network roundtrips
- **PMOS Calibration**: Deterministic BMR/TDEE calculation with a 15% metabolic penalty to provide clinically relevant targets for insulin-resistant profiles
