# 📖 Project Details: MacroManager

## 1. Introduction
MacroManager is an intelligent nutrition tracking system designed specifically for PCOS/PCOD dietary management. It bridges the gap between natural language food logging and precise nutritional analysis. The system is designed to handle the ambiguity of human speech and the complexity of regional cuisines, ensuring that every calorie is accounted for accurately. 

A one-shot onboarding flow extracts user biometrics from free-text bios and calculates PCOS-calibrated macro targets to help users manage insulin resistance and metabolic health.

---

## 2. High-Level Design (HLD)
 
### 2.1 Architecture Overview
The system employs a decoupled **Client-Server Architecture**:
 
*   **Frontend (Streamlit)**: A high-fidelity dashboard for logging food and visualizing progress. It utilizes a **"Plain Notebook" aesthetic** (Courier Prime typography, grid-paper background) to minimize cognitive load and create an emotionally intimate user experience. It features an interactive macro HUD, Integrated Voice-to-Log, and a granular, record-based Food Journal with inline editing.
*   **Backend (FastAPI)**: An asynchronous orchestrator managing data flow between the LLM, nutrition database, user logs, and the vision pipeline. It implements **timezone-aware query logic** using SQLite's `localtime` to ensure data consistency across server/client boundaries.
*   **Nutritional Intelligence**: A hybrid system combining a local FTS5-powered database with a Gemma 4-driven web-search agent (Tavily API) and a **Clinical Copilot**. The system includes a **Medical Firewall** to ensure safety boundaries are maintained, prioritizing professional medical referral over AI diagnosis. Backend prompts are specifically **primed with PCOS metabolic context** to provide specialized, context-aware dietary guidance.
*   **Persistence Layer (SQLite)**: Two specialized databases:
    *   `foodbank.db`: Static and learned food nutrition data.
    *   `macros.db`: User meal logs and goal settings.
*   **Vision Pipeline**: A multimodal module that extracts food items from images with environment-aware portion size estimation.
*   **Sovereign Memory**: A personalized dietary glossary (`personal_glossary.md`) and an inline dashboard input that stores user-specific facts (e.g., utensil sizes, dietary preferences) to enhance extraction accuracy.
*   **Offline Sync Queue**: A robust background mechanism that captures unverified data while offline and automatically synchronizes with authoritative sources via a heartbeat lifecycle.
*   **Onboarding Engine**: LLM-driven attribute extraction from free-text bios, followed by deterministic PCOS-calibrated macro calculation.


### 2.2 Data Flow: The Async Pipeline
To ensure a snappy UX, the system uses a **Job-Status model** instead of blocking requests:

**1. Input Phase**
`User Text/Voice` $\rightarrow$ `ExtractionService.extract_items()` $\rightarrow$ **Returns `meal_id` & `items` instantly to UI**
`User Dietary Query` $\rightarrow$ `PlannerService.plan()` $\rightarrow$ `Router` $\rightarrow$ `Knowledge Loader` $\rightarrow$ `Clinical Copilot` $\rightarrow$ **Returns tailored plan with safety disclaimer**

**2. Background Resolution (Async)**
The server triggers a background task to resolve nutrition for each item in parallel:
`Local DB Check` $\rightarrow$ `Canonicalization (Fuzzy Match)` $\rightarrow$ `Authoritative Web Search` $\rightarrow$ `General Search` $\rightarrow$ `LLM Estimate` $\rightarrow$ `DB Upsert`

**3. UI Synchronization**
The Frontend polls `GET /log/status/{meal_id}` $\rightarrow$ Updates item spinners to checkmarks as they resolve $\rightarrow$ Refreshes Dashboard on completion.

**4. Finalization**
`Atwater Guardrail` (Calorie Validation) $\rightarrow$ `Persistence` $\rightarrow$ `Daily Summary Update`

---

## 3. Low-Level Design (LLD)

### 3.1 Core Components

#### A. `DatabaseManager`
*   **FTS5 Search**: Uses Full-Text Search for alias-based lookups (e.g., "chawal" $\rightarrow$ "Rice").
*   **Temporal Aggregation**: Calculates weekly summaries based on the static calendar week (Monday-Sunday).
*   **Schema Evolution**: Implements automated migrations to ensure database stability.

#### B. `FoodbankService`
*   **Canonicalization Layer**: Uses Levenshtein-based fuzzy matching (`difflib`) to resolve typos or name variations to existing DB entries, bypassing slow web searches.
*   **L1 In-Memory Cache**: High-speed dictionary cache for frequent items to eliminate redundant DB/Network roundtrips.
*   **Learning Mode**: Automatically persists newly discovered foods to the database to reduce future LLM dependency.

#### C. `ExtractionService`
*   **Unified Resolver**: A centralized engine (`_resolve_and_build_log`) that handles recipe expansion and nutrition resolution identically for both text and vision paths.
*   **Async Decoupling**: Separates item extraction from nutritional resolution to prevent API timeouts.
*   **Vision Analysis**: Implements a Two-Step reasoning process (**Analysis $\rightarrow$ Extraction**). It uses environment rules (`Home` vs `Wild`) to estimate portion sizes accurately.

#### E. `PlannerService` (Clinical Copilot)
Implements a three-stage routing pipeline to provide empathetic and safe dietary guidance:
1. **Router**: Analyzes the user query to determine the intent (e.g., general advice, specific meal plan, or acute medical concern).
2. **Knowledge Loader**: Fetches relevant PCOS nutrition constraints from the wiki/knowledge base.
3. **Clinical Copilot**: Synthesizes a tailored plan using the `meal_copilot` prompt, strictly adhering to a **Medical Firewall** that refers acute symptoms or prescription requests to a physician.
1.  **BMR (Mifflin-St Jeor)**: `(10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161` (Age default: 25).
2.  **TDEE**: `BMR * activity_level`
    *   *Sedentary*: 1.2 | *Light*: 1.375 | *Moderate*: 1.55 | *Active*: 1.725
3.  **Goal Modifier**: Applied to TDEE: `Lose: -500` | `Maintain: 0` | `Gain: +500`.
4.  **PCOS Penalty**: `target_calories = adjusted_tdee * 0.85` (15% metabolic reduction).
5.  **Macro Split (40/35/25)**:
    *   **Protein**: `(target_calories * 0.4) / 4`
    *   **Fat**: `(target_calories * 0.35) / 9`
    *   **Carbs**: `(target_calories * 0.25) / 4`

---

## 4. Gemma Integration

The system leverages **Gemma 4 (`gemma4:e2b`)** as its cognitive core for multiple specialized tasks:

| Task | Implementation | Key Strategy |
| :--- | :--- | :--- |
| **Text Extraction** | `ExtractionService` | High-recall, single-pass extraction from natural language. |
| **Vision Analysis** | `ExtractionService` | Multimodal (Image + Text) analysis for item identification and portion estimation. |
| **Nutritional Search** | `FoodbankService` | Validates search results against "Sources of Truth" to assign confidence tiers. |
| **User Onboarding** | `OnboardingService` | Attribute extraction from free-text bios to fuel the calibration engine. |

**Operational Guardrails**:
*   **Determinism**: `temperature = 0.0` is used across all calls to ensure consistent outputs.
*   **Concurrency**: A global `asyncio.Semaphore` prevents local LLM (Ollama) saturation during parallel item resolution.
*   **Prompt Management**: All prompts are externalized in `prompts.yaml` for rapid tuning without code changes.

---

## 5. Functional Specifications

### 5.1 Feature Matrix
| Feature | Description | Implementation |
| :--- | :--- | : |
| **Async Logging** | Instant item extraction $\rightarrow$ Background resolution | Job-Status Model + BackgroundTasks |
| **Fuzzy Matching** | Maps "Budhani Chipss" $\rightarrow$ "Budhani Potato Chips" | `difflib` Canonicalization Layer |
| **Vision Logging** | Image $\rightarrow$ Item + Weight extraction | Multimodal Gemma 4 + Env Rules |
| **Clinical Copilot** | AI-driven meal planning with integrated Medical Firewall | PlannerService $\rightarrow$ Router $\rightarrow$ Copilot |
| **Medical Firewall** | Safety guardrail to prevent AI medical diagnosis | System Role Boundaries |
| **Regional Support** | Complex dish decomposition using Expert Estimator + Category Fallback | Recipe Expansion $\rightarrow$ Ingredient-Based Inference |
| **PCOS Calibration** | Bio-text $\rightarrow$ Calibrated macro targets | Onboarding Engine + metabolic penalty |
| **Atwater Guardrail** | Corrects LLM calorie deviations > 20% | `Cals = P*4 + C*4 + F*9` |
| **Interactive HUD** | 3D Glass flip-cards for macros and sub-macros | Custom CSS/HTML + Streamlit |

### 5.2 API Reference
| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/planner` | `POST` | Clinical Copilot: Route query $\rightarrow$ Knowledge $\rightarrow$ Tailored dietary plan. |
| `/log/start` | `POST` | Extract items from text; start background resolution. Returns `meal_id`. |
| `/log/status/{id}` | `GET` | Poll resolution status (`processing` $\rightarrow$ `completed`). |
| `/vision-log` | `POST` | Multimodal extraction from image $\rightarrow$ Resolve $\rightarrow$ Save. |
| `/onboard` | `POST` | Bio-text $\rightarrow$ Calculate PCOS targets $\rightarrow$ Save goals. |
| `/summary` | `GET` | Daily aggregated totals + goals + weekly buffer. |
| `/meals` | `GET` | Chronological list of today's food items. |
| `/goals` | `POST` | Manual update of macro targets. |
| `/clear` | `DELETE` | Reset daily progress. |

---
 
## 7. UI/UX & Logic Overhaul (Sprints 7-8)
 
The system underwent a comprehensive 4-phase overhaul to transition from a "prototype" feel to a "clinical notebook" experience, focusing on emotional intimacy and data granularity.
 
### Phase 1: Notebook Aesthetic & HUD
- **Design Language**: Transitioned to a "Plain Notebook" style using `Courier Prime` typography and a grid-paper CSS background.
- **Emotional Design**: Replaced high-contrast "Glass" elements with muted, soft tones to reduce user anxiety associated with "overflowing" macros.
- **HUD Refinement**: Simplified the macro rings and introduced "Empathetic Messaging" that provides kind, non-judgmental feedback based on current progress.
 
### Phase 2: Timezone Alignment & API Expansion
- **The Ghost Entry Fix**: Resolved a critical bug where server UTC timestamps caused meals to appear on the wrong day or journals to appear empty. implemented `date(timestamp, 'localtime')` in all SQLite queries.
- **Granular API**: Expanded the API from simple "clear all" to a full CRUD suite:
    - `GET /meals` (Date-filtered retrieval)
    - `PATCH /meals/{id}` (Item-level updates)
    - `DELETE /meals/{id}` (Targeted deletion)
    - `DELETE /meals/clear` (Bulk date-based clear)
 
### Phase 3: Intelligence Layer Integration
- **Clinical Copilot**: Fully integrated the Copilot's dietary advice engine into the dashboard with a low-contrast, greyish text style for subtle guidance.
- **Insulin Guardrails**: Re-implemented the "130% Daily Limit" logic in the weekly view to prevent dangerous insulin spikes by locking the weekly buffer when daily limits are breached.
- **Inline Memory**: Moved Sovereign Memory from a disruptive dialog to a seamless inline input section.
 
### Phase 4: Tabular Food Journal & Inline Editing
- **High-Fidelity Journal**: Implemented a sticky-header tabular view for the daily log.
- **Inline Quantity Scaling**: Introduced a ratio-based editing system. Changing the weight of a food item automatically scales its protein, carbs, and fat proportionally on the server.
- **Schema Hardening**: Implemented strict Pydantic validation in the update pipeline to ensure `400 Bad Request` errors are eliminated during manual edits.
- **Layout Optimization**: Applied smart wrapping for long food names and `nowrap` constraints for 3-digit numerical blocks to maintain table alignment.

