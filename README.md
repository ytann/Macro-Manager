# MacroManager
 
AI-powered nutrition tracking for PCOS/PCOD management. Natural language food logs -> precise macro-nutrient data. Multi-pass extraction pipeline + authoritative "Source of Truth" learning system + offline-capable sync queue + **vision-based food extraction (Home vs. Wild)** + **one-shot onboarding with PCOS-calibrated macro targets**.
 
## Flow

`User Input` -> `Item Extraction` -> `Background Resolution` -> `Status Polling` -> `Persistence` -> `Dashboard`
`Onboarding Bio Text` -> `LLM Attribute Extraction` -> `PCOS Baseline Math (BMR/TDEE/Penalty/Macros)` -> `Goal Persistence`
 
## Quick Start
 
```bash
# Prerequisites: Ollama running, gemma4:e2b pulled
pip install -r requirements.txt
 
# Terminal 1: Backend API
export PYTHONPATH=$PYTHONPATH:.
python -m app.api
 
# Terminal 2: Frontend Dashboard
export PYTHONPATH=$PYTHONPATH:.
streamlit run app/frontend.py
```
 
## Project Structure
 
```
MacroManager/
  app/
    __init__.py
    api.py                    # FastAPI endpoints + heartbeat lifecycle
    frontend.py               # Streamlit dashboard
    core/
      config.py               # Centralized configuration
      logger.py               # Standardized logging utility
      llm.py                  # Global LLM concurrency control (Semaphore)
    schemas/
      food_schemas.py         # Pydantic: Macros, SubMacros, FoodItem, FoodLog
    services/
      database.py             # DatabaseManager: SQLite FTS5 + meals
      foodbank.py             # FoodbankService: lookups, web search, offline sync
      extraction.py           # ExtractionService: optimized single-pass LLM parsing
      onboarding.py           # OnboardingService: PCOS baseline macros from bio text
  prompts/
    prompts.yaml              # Externalized LLM prompts
  scripts/
    ingest_csv.py             # CSV -> foodbank importer
  tests/                      # pytest suites
  debug/                      # non-pytest diagnostic scripts
  wiki/                       # Agent routing index, architecture, QA rules
    index.md                  # Agent routing table
    QA_Failures.md            # Lint rules and failure patterns
    logic/
      Architecture.md         # Component map, data flow, DB schema
      FoodLearning.md         # Identification, recipe expansion, anti-hallucination
      FoodLogSchema.md        # Pydantic model definitions
      OfflineSync.md          # Sync queue, heartbeat, retry limits
      audit_logic.md          # Implementation steps for audit fixes
  raw/                        # Cloud-generated logic specs
  audit_logs.md             # Consolidated codebase audit and fix logs
  ProjectDetails.md           # Detailed HLD/LLD documentation
  requirements.txt
```
 
## Key Architecture
  
| Component | Description |
|---|---|
| **Plain Notebook UI** | High-fidelity, emotionally intimate aesthetic (Courier Prime, grid-paper) for reduced cognitive load |
| **Timezone-Aware Logs** | Server-side `localtime` alignment in SQLite to prevent date-mismatch/ghost entries |
| **Async parallel** | `asyncio.gather` resolves all food items concurrently |
| **Self-Verifying Extraction** | Single-pass extraction with internal self-verification to maximize recall and minimize latency |
| **Offline sync queue** | Cached data returned immediately when offline; unverified items queued for heartbeat sync |
| **Source of Truth** | Authoritative web search (Tavily) with LLM validation, confidence tiers |
| **Unified Resolver** | Shared resolution engine for text and vision paths ensuring consistent macro calculation and recipe expansion |
| **Recipe expansion** | Complex dishes decomposed into base ingredients before macro calculation |
| **Regional Support** | Complex dish decomposition using Expert Estimator + Category Fallback | Recipe Expansion $\rightarrow$ Ingredient-Based Inference |
| **Clinical Copilot** | AI-driven meal planning and dietary advice with built-in Medical Firewall | PlannerService + Router + Copilot Prompts |
| **Medical Firewall** | Strict boundaries to prevent medical diagnosis/prescriptions | System Role Guardrails in PlannerService |
| **Atwater guardrail** | Calorie = P*4 + C*4 + F*9, corrects LLM deviations >20% |
| **FTS5 food search** | Full-text search for alias-based food lookups (case-insensitive) |
| **L1 In-Memory Cache** | High-speed lookup for frequent items to bypass DB/Web latency |
| **Canonicalization Layer** | Fuzzy matching (Levenshtein) to map typos/variations to existing DB entries, minimizing slow web searches |
| **Advanced Macros** | Tracks Sugar, Saturated Fat, and Unsaturated Fat alongside primary macros |
| **PCOS Onboarding** | LLM extracts bio attributes -> Mifflin-St Jeor BMR -> TDEE -> goal modifier -> 0.85 PCOS penalty -> 40/35/25 macro split |
| **Global LLM Throttle** | Semaphore-based concurrency control to prevent local LLM (Ollama) saturation |
| **Telemetry** | Standardized logging across all services for traceability |
| **Granular Journal CRUD** | Inline quantity editing with ratio-based macro scaling and server-side validation |

 
## API Endpoints
  
- `POST /planner` — Clinical Copilot: Route query $\rightarrow$ Knowledge $\rightarrow$ Empathetic Dietary Plan
- `POST /log/start` — Fast item extraction, returns `meal_id` for background resolution
- `GET /log/status/{meal_id}` — Poll status of background nutrition resolution
- `POST /log` — Backward compatibility: synchronous parse and save
- `POST /vision-log` — Extract food from image (base64), resolve nutrition, save meal. Supports `Home`/`Wild` environment weighting and optional `hint` for better item identification.
- `POST /onboard` — One-shot PCOS baseline: LLM extracts height/weight/activity/goal from bio text, calculates Mifflin-St Jeor BMR, TDEE, applies PCOS penalty (0.85x), sets daily macro goals
- `GET /summary` — Daily aggregated totals + goals AND static calendar week summary (Supports `date` param)
- `POST /goals` — Update user macro targets
- `GET /meals` — Chronological list of food items for a specific date
- `PATCH /meals/{meal_id}` — Update meal items with automatic macro recalculation
- `DELETE /meals/{meal_id}` — Remove a specific meal record
- `DELETE /meals/clear` — Reset all meals for a specific date
- `GET /pending-count` — Verification queue size
- `GET /sync-status` — Last sync timestamp
- `POST /verify-queue` — Manual sync trigger
 
 
## See Also
 
- [ProjectDetails.md](./ProjectDetails.md) for full HLD/LLD
- [wiki/index.md](./wiki/index.md) for agent routing table
