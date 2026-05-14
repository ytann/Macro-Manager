# Agent Routing Table

- Pydantic schemas for food logs (Macros, SubMacros, FoodItem, FoodLog) -> [[wiki/logic/FoodLogSchema.md]]
- Project architecture, component map, data flow, database schema -> [[wiki/logic/Architecture.md]]
- Food identification flow, recipe expansion, anti-hallucination measures -> [[wiki/logic/FoodLearning.md]]
- Offline sync queue logic, heartbeat, retry limits, verification pipeline -> [[wiki/logic/OfflineSync.md]]
- PCOS one-shot onboarding, BMR/TDEE math, macro split logic -> [[wiki/logic/Onboarding.md]]
- QA rules (lint checks, guardrails, failure patterns to avoid) -> [[wiki/QA_Failures.md]]
- Database operations, init logic, connection management, weekly aggregation -> [[app/services/database.py]]
- Foodbank service (Consolidated nutrition resolution, L1 caching, DB lookups, web search, estimates, upsert, verification) -> [[app/services/foodbank.py]]
- Extraction service (unified resolution engine, two-pass LLM parsing, recipe expansion, async nutrition resolution) -> [[app/services/extraction.py]]
- Vision-based food extraction (unified resolution, image-to-items pipeline, Home vs. Wild environment rules, multimodal payload formatting, user hints) -> [[app/services/extraction.py]] (extract_from_image method)
- Streamlit vision client utility (base64 encoding, API communication for vision logs) -> [[app/utils/vision_client.py]]
- API endpoints, heartbeat lifecycle, daily/weekly summaries, vision-log handler -> [[app/api.py]]
- Vision extraction prompt (environment-aware portion estimation for Home/Wild) -> [[prompts/prompts.yaml]] (extraction.vision_estimate)
- CSV ingestion script for seeding foodbank -> [[scripts/ingest_csv.py]]
- Audit: codebase issues, fix plans, and offline sync details -> [[audit_logs.md]]
- Implementation steps for audit fixes -> [[wiki/logic/audit_logic.md]]
