# MacroManager
 
AI-powered nutrition tracking. Natural language food logs -> precise macro-nutrient data. Multi-pass extraction pipeline + authoritative "Source of Truth" learning system + offline-capable sync queue + **vision-based food extraction (Home vs. Wild)**.
 
## Flow
 
`User Input` -> `Two-Pass LLM Extraction` -> `Async Parallel Nutrition Resolution` -> `Atwater Guardrail` -> `Persistence` -> `Dashboard`
 
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
    schemas/
      food_schemas.py         # Pydantic: Macros, SubMacros, FoodItem, FoodLog
    services/
      database.py             # DatabaseManager: SQLite FTS5 + meals
      foodbank.py             # FoodbankService: lookups, web search, offline sync
      extraction.py           # ExtractionService: two-pass LLM parsing
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
| **Async parallel** | `asyncio.gather` resolves all food items concurrently |
| **Two-pass extraction** | 1st pass extracts, 2nd pass (verification guardrail) catches missed items |
| **Offline sync queue** | Cached data returned immediately when offline; unverified items queued for heartbeat sync |
| **Source of Truth** | Authoritative web search (DuckDuckGo) with LLM validation, confidence tiers |
| **Recipe expansion** | Complex dishes decomposed into base ingredients before macro calculation |
| **Atwater guardrail** | Calorie = P*4 + C*4 + F*9, corrects LLM deviations >20% |
| **FTS5 food search** | Full-text search for alias-based food lookups (case-insensitive) |
| **L1 In-Memory Cache** | High-speed lookup for frequent items to bypass DB/Web latency |
| **Advanced Macros** | Tracks Sugar, Saturated Fat, and Unsaturated Fat alongside primary macros |
| **Telemetry** | Standardized logging across all services for traceability |
 
## API Endpoints
  
- `POST /log` — Parse text, calculate macros, save meal
- `POST /vision-log` — Extract food from image (base64), resolve nutrition, save meal. Supports `Home`/`Wild` environment weighting
- `GET /summary` — Daily aggregated totals + goals AND weekly rolling summary
- `POST /goals` — Update user macro targets
- `GET /meals` — All items logged today
- `DELETE /clear` — Reset daily progress
- `GET /pending-count` — Verification queue size
- `GET /sync-status` — Last sync timestamp
- `POST /verify-queue` — Manual sync trigger
 
 
## See Also
 
- [ProjectDetails.md](./ProjectDetails.md) for full HLD/LLD
- [wiki/index.md](./wiki/index.md) for agent routing table
