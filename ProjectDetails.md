# 📖 Project Details: MacroManager

## 1. Introduction
MacroManager is an intelligent nutrition tracking system designed specifically for **PMOS (prev. PCOS)/PCOD** dietary management. It bridges the gap between natural language food logging and precise nutritional analysis, focusing on metabolic health, insulin resistance, and emotional intimacy in the user experience.

## 2. High-Level Design (HLD)

### 2.1 Architecture Overview
The system employs a decoupled **Client-Server Architecture**:

*   **Frontend (Streamlit)**: A high-fidelity dashboard utilizing a **"Plain Notebook" aesthetic** (Courier Prime typography, grid-paper background). It prioritizes a low-anxiety interface with an interactive macro HUD and a granular, record-based Food Journal.
*   **Backend (FastAPI)**: An asynchronous orchestrator managing data flow between the LLM, nutrition database, user logs, and the vision pipeline. It implements **timezone-aware query logic** using SQLite's `localtime` to ensure data consistency across server/client boundaries.
*   **Nutritional Intelligence**: A hybrid system combining a local FTS5-powered database with a Gemma 4-driven web-search agent (Tavily API) and a **Clinical Copilot**. A **Medical Firewall** ensures safety by referring acute medical concerns to professional physicians.
*   **Persistence Layer (SQLite)**: 
    *   `foodbank.db`: Static and learned food nutrition data.
    *   `macros.db`: User meal logs and goal settings.
*   **Vision Pipeline**: A multimodal module extracting food items from images with environment-aware portion size estimation (`Home` vs `Wild`).
*   **Sovereign Memory**: A personalized dietary glossary (`personal_glossary.md`) that stores user-specific facts (e.g., utensil sizes, frequent meal variations) to enhance extraction accuracy.
*   **Offline Sync Queue**: A background mechanism that captures unverified data while offline and synchronizes with authoritative sources via a heartbeat lifecycle.
*   **Onboarding Engine**: LLM-driven attribute extraction from free-text bios, followed by deterministic PMOS-calibrated macro calculation.

### 2.2 Data Flow: The Async Pipeline
To ensure a snappy UX, the system uses a **Job-Status model**:

1.  **Input Phase**: User text or image is sent $\rightarrow$ `ExtractionService` identifies items $\rightarrow$ **Returns `meal_id` & items instantly to UI**.
2.  **Background Resolution (Async)**: The server resolves nutrition for each item in parallel: `Local DB` $\rightarrow$ `Fuzzy Match` $\rightarrow$ `Web Search` $\rightarrow$ `LLM Estimate` $\rightarrow$ `DB Upsert`.
3.  **UI Synchronization**: Frontend polls `GET /log/status/{meal_id}` $\rightarrow$ updates item spinners to checkmarks.
4.  **Finalization**: `Atwater Guardrail` validates calories $\rightarrow$ `Persistence` $\rightarrow$ `Daily Summary Update`.

---

## 3. Low-Level Design (LLD)

### 3.1 Core Components

#### A. `DatabaseManager`
*   **FTS5 Search**: Full-text search for alias-based lookups (e.g., "roti" $\rightarrow$ "Chapati").
*   **Temporal Aggregation**: Calculates weekly summaries based on the static calendar week (Monday-Sunday).

#### B. `FoodbankService`
*   **Canonicalization Layer**: Uses Levenshtein-based fuzzy matching to resolve typos or name variations, bypassing slow web searches.
*   **L1 In-Memory Cache**: High-speed dictionary cache for frequent items to eliminate redundant DB/Network roundtrips.

#### C. `ExtractionService`
*   **Unified Resolver**: A centralized engine that handles recipe expansion and nutrition resolution identically for both text and vision paths.
*   **Vision Analysis**: Employs a Two-Step reasoning process (**Analysis $\rightarrow$ Extraction**) using environment rules (`Home` vs `Wild`) to estimate portion sizes.

#### D. `PlannerService` (Clinical Copilot)
Provides empathetic and safe dietary guidance via a three-stage pipeline:
1.  **Router**: Determines user intent (general advice vs. specific meal plan).
2.  **Knowledge Loader**: Fetches relevant PMOS nutrition constraints from the wiki.
3.  **Clinical Copilot**: Synthesizes a tailored plan adhering to a **Medical Firewall**.

#### E. `OnboardingService` (PMOS Calibration)
1.  **BMR (Mifflin-St Jeor)**: $\text{BMR} = (10 \times \text{weight\_kg}) + (6.25 \times \text{height\_cm}) - (5 \times \text{age}) - 161$.
2.  **TDEE**: $\text{BMR} \times \text{activity\_level}$.
3.  **Goal Modifier**: Adjusted for weight loss/maintenance/gain.
4.  **PMOS Penalty**: $\text{Target Calories} = \text{adjusted\_TDEE} \times 0.85$ (15% metabolic reduction for insulin resistance).
5.  **Macro Split (40/35/25)**: Protein (40%), Fat (35%), Carbs (25%).

---

## 4. Gemma Integration
The system leverages **Gemma 4 (`gemma4:e2b`)** as its cognitive core:

| Task | Implementation | Key Strategy |
| :--- | :--- | :--- |
| **Text Extraction** | `ExtractionService` | High-recall, single-pass extraction. |
| **Vision Analysis** | `ExtractionService` | Multimodal (Image + Text) analysis + Env rules. |
| **Nutritional Search** | `FoodbankService` | Validates search results against "Sources of Truth". |
| **User Onboarding** | `OnboardingService` | Attribute extraction from free-text bios. |

---

## 5. Functional Specifications

### 5.1 Feature Matrix
| Feature | Description | Implementation |
| :--- | :--- | :--- |
| **Async Logging** | Instant extraction $\rightarrow$ Background resolution | Job-Status Model + BackgroundTasks |
| **Fuzzy Matching** | Maps typos $\rightarrow$ canonical food entries | `difflib` Canonicalization Layer |
| **Vision Logging** | Image $\rightarrow$ Item + Weight extraction | Multimodal Gemma 4 + Env Rules |
| **Clinical Copilot** | AI-driven meal planning + Medical Firewall | PlannerService $\rightarrow$ Router $\rightarrow$ Copilot |
| **PMOS Calibration** | Bio-text $\rightarrow$ Calibrated macro targets | Onboarding Engine + metabolic penalty |
| **Inline Editing** | Ratio-based quantity scaling in the journal | `PATCH /meals/{id}` + proportionally scaled macros |
| **Timezone Fix** | Prevents "Ghost entries" across UTC/Local | SQLite `localtime` in all queries |

### 5.2 API Reference
| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/planner` | `POST` | Clinical Copilot: Route query $\rightarrow$ Knowledge $\rightarrow$ Plan |
| `/log/start` | `POST` | Extract items $\rightarrow$ returns `meal_id` |
| `/log/status/{id}` | `GET` | Poll resolution status |
| `/vision-log` | `POST` | Image $\rightarrow$ Extract $\rightarrow$ Resolve $\rightarrow$ Save |
| `/onboard` | `POST` | Bio-text $\rightarrow$ Calculate PMOS targets $\rightarrow$ Save |
| `/summary` | `GET` | Daily aggregates + goals + weekly buffer |
| `/meals` | `GET` | Chronological retrieval for a specific date |
| `/goals` | `POST` | Manual update of macro targets |

---

## 6. UI/UX & Logic Overhaul (Sprints 7-8)

The system transitioned from a prototype to a "clinical notebook" experience:

### Phase 1: Notebook Aesthetic & HUD
- **Design Language**: Transitioned to a "Plain Notebook" style using `Courier Prime` typography and a grid-paper CSS background.
- **Emotional Design**: Replaced high-contrast "Glass" elements with muted, soft tones to reduce user anxiety.

### Phase 2: Timezone Alignment & API Expansion
- **The Ghost Entry Fix**: Resolved UTC mismatch bugs using `date(timestamp, 'localtime')` in all SQLite queries.
- **Granular API**: Expanded to a full CRUD suite for meal items (GET, PATCH, DELETE).

### Phase 3: Intelligence Layer Integration
- **Clinical Copilot**: Integrated dietary advice engine into the dashboard with a low-contrast, subtle text style.
- **Insulin Guardrails**: Implemented the "130% Daily Limit" logic in the weekly view to prevent dangerous insulin spikes.

### Phase 4: Tabular Food Journal & Inline Editing
- **High-Fidelity Journal**: Implemented a sticky-header tabular view for the daily log.
- **Inline Quantity Scaling**: Changing the weight of a food item automatically scales its protein, carbs, and fat proportionally on the server.
- **Schema Hardening**: Strict Pydantic validation in the update pipeline to ensure data integrity during manual edits.
