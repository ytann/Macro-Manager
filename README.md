# MacroManager

AI-powered nutrition tracking. Natural language food logs -> precise macro-nutrient data. Multi-pass extraction pipeline + authoritative "Source of Truth" learning system + offline-capable sync queue.

## Flow

`User Input` -> `Two-Pass LLM Extraction` -> `Async Parallel Nutrition Resolution` -> `Atwater Guardrail` -> `Persistence` -> `Dashboard`

## Quick Start

```bash
# Prerequisites: Ollama running, llama3.1:latest pulled
pip install -r requirements.txt

# Terminal 1: Backend API
python app/api.py

# Terminal 2: Frontend Dashboard
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
  audit_report.md             # Full codebase audit
  audit_offline_sync.md       # Offline sync specific audit
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
| **FTS5 food search** | Full-text search for alias-based food lookups |

## API Endpoints

- `POST /log` — Parse text, calculate macros, save meal
- `GET /summary` — Daily aggregated totals + goals
- `GET /meals` — All items logged today
- `DELETE /clear` — Reset daily progress
- `GET /pending-count` — Verification queue size
- `GET /sync-status` — Last sync timestamp
- `POST /verify-queue` — Manual sync trigger

## See Also

- [ProjectDetails.md](./ProjectDetails.md) for full HLD/LLD
- [wiki/index.md](./wiki/index.md) for agent routing table