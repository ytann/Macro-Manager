# Agent Routing Table
 
- Pydantic schemas for food logs (Macros, SubMacros, FoodItem, FoodLog) -> [[wiki/logic/FoodLogSchema.md]]
- Project architecture, component map, data flow, database schema -> [[wiki/logic/Architecture.md]]
- Clinical Copilot (Routing Engine, Medical Firewall, Planner Service) -> [[app/services/planner.py]]
- Food identification flow, recipe expansion, anti-hallucination measures -> [[wiki/logic/FoodLearning.md]]
- Offline sync queue logic, heartbeat, retry limits, verification pipeline -> [[wiki/logic/OfflineSync.md]]
- PMOS one-shot onboarding, BMR/TDEE math, macro split logic -> [[wiki/logic/Onboarding.md]]
- QA rules (lint checks, guardrails, failure patterns to avoid) -> [[wiki/QA_Failures.md]]
- Database operations, init logic, connection management, weekly aggregation -> [[app/services/database.py]]
- Foodbank service (Consolidated nutrition resolution, canonicalization layer/fuzzy matching, L1 caching, DB lookups, web search, estimates, upsert, verification) -> [[app/services/foodbank.py]]
- Extraction service (unified resolution engine, self-verifying single-pass LLM parsing, recipe expansion, async nutrition resolution, global LLM concurrency control, async job-status pipeline) -> [[app/services/extraction.py]]
- Vision-based food extraction (unified resolution, image-to-items pipeline, Home vs. Wild environment rules, multimodal payload formatting, user hints) -> [[app/services/extraction.py]] (extract_from_image method)
- Streamlit vision client utility (base64 encoding, API communication for vision logs) -> [[app/utils/vision_client.py]]
- API endpoints, heartbeat lifecycle, daily/weekly summaries, vision-log handler -> [[app/api.py]]
- Vision extraction prompt (environment-aware portion estimation for Home/Wild) -> [[prompts/prompts.yaml]] (extraction.vision_estimate)
- CSV ingestion script for seeding foodbank -> [[scripts/ingest_csv.py]]
- Audit: codebase issues, fix plans, and offline sync details -> [[audit_logs.md]]
- Implementation steps for audit fixes -> [[wiki/logic/audit_logic.md]]
- **Gemma4:e2b PMOS Nutrition Knowledge Base** (compressed for small LLM reasoning) -> [[wiki/pmos_nutrition/INDEX.md]]
  - PMOS IR pathophysiology (IRS-1 block, tissue profiles, ovarian paradox) -> [[wiki/pmos_nutrition/01_IR_Pathophysiology.md]]
  - Macronutrient strategy + meal recommendations (40/35/25, VPF sequencing, daily allocation algorithm) -> [[wiki/pmos_nutrition/02_Macronutrient_Strategy.md]]
  - Chrononutrition (diurnal IR rhythm, melatonin effects, LEO carryover, meal timing rules) -> [[wiki/pmos_nutrition/03_Chrononutrition.md]]
  - Inflammation, dysbiosis, fiber mechanics (DOGMA loop, fiber thresholds 28-36g, omega-3 vs MUFA) -> [[wiki/pmos_nutrition/04_Inflammation_Fiber_Lipids.md]]
- **Recent UI/UX & Logic Overhaul** (Notebook aesthetic, Timezone alignment, Granular Journal CRUD, Inline Editing) -> [[ProjectDetails.md]]

