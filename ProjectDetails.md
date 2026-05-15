# 📖 Project Details: MacroManager

## 1. Introduction
MacroManager is an intelligent nutrition tracking system designed specifically for PCOS/PCOD dietary management. It bridges the gap between natural language food logging and precise nutritional analysis. The system is designed to handle the ambiguity of human speech and the complexity of regional cuisines, ensuring that every calorie is accounted for accurately. 

A one-shot onboarding flow extracts user biometrics from free-text bios and calculates PCOS-calibrated macro targets to help users manage insulin resistance and metabolic health.

---

## 2. High-Level Design (HLD)

### 2.1 Architecture Overview
The system employs a decoupled **Client-Server Architecture**:

*   **Frontend (Streamlit)**: A high-fidelity dashboard for logging food and visualizing progress. It features an interactive 3D Glass HUD for macro tracking and integrated Voice-to-Log capabilities.
*   **Backend (FastAPI)**: An asynchronous orchestrator managing data flow between the LLM, nutrition database, user logs, and the vision pipeline.
*   **Nutritional Intelligence**: A hybrid system combining a local FTS5-powered database with a Gemma 4-driven web-search agent (Tavily API). The backend prompts are specifically **primed with PCOS metabolic context** to move beyond generic FDA guidelines and instead provide specialized, context-aware dietary guidance.
*   **Persistence Layer (SQLite)**: Two specialized databases:
    *   `foodbank.db`: Static and learned food nutrition data.
    *   `macros.db`: User meal logs and goal settings.
*   **Vision Pipeline**: A multimodal module that extracts food items from images with environment-aware portion size estimation.
*   **Sovereign Memory**: A personalized dietary glossary (`personal_glossary.md`) that stores user-specific facts (e.g., utensil sizes, dietary preferences) to enhance extraction accuracy.
*   **Offline Sync Queue**: A robust background mechanism that captures unverified data while offline and automatically synchronizes with authoritative sources via a heartbeat lifecycle.
*   **Onboarding Engine**: LLM-driven attribute extraction from free-text bios, followed by deterministic PCOS-calibrated macro calculation.

### 2.2 Data Flow: The Async Pipeline
To ensure a snappy UX, the system uses a **Job-Status model** instead of blocking requests:

**1. Input Phase**
`User Text/Voice` $\rightarrow$ `ExtractionService.extract_items()` $\rightarrow$ **Returns `meal_id` & `items` instantly to UI**

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

#### D. `OnboardingService` (PCOS Calibration)
Extracts user biometrics via LLM and applies the following deterministic logic:

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
| **Regional Support** | Complex dish decomposition (e.g., Poha) | Recipe Expansion $\rightarrow$ Base Ingredients |
| **PCOS Calibration** | Bio-text $\rightarrow$ Calibrated macro targets | Onboarding Engine + metabolic penalty |
| **Atwater Guardrail** | Corrects LLM calorie deviations > 20% | `Cals = P*4 + C*4 + F*9` |
| **Interactive HUD** | 3D Glass flip-cards for macros and sub-macros | Custom CSS/HTML + Streamlit |

### 5.2 API Reference
| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/log/start` | `POST` | Extract items from text; start background resolution. Returns `meal_id`. |
| `/log/status/{id}` | `GET` | Poll resolution status (`processing` $\rightarrow$ `completed`). |
| `/vision-log` | `POST` | Multimodal extraction from image $\rightarrow$ Resolve $\rightarrow$ Save. |
| `/onboard` | `POST` | Bio-text $\rightarrow$ Calculate PCOS targets $\rightarrow$ Save goals. |
| `/summary` | `GET` | Daily aggregated totals + goals + weekly buffer. |
| `/meals` | `GET` | Chronological list of today's food items. |
| `/goals` | `POST` | Manual update of macro targets. |
| `/clear` | `DELETE` | Reset daily progress. |

---

## 6. Design Decisions & Trade-offs
*   **SQLite FTS5**: Chosen over standard SQL for superior alias searching and performance with large nutrition datasets.
*   **Local LLM (Ollama)**: Prioritizes user privacy and eliminates API costs. The `gemma4:e2b` model provides the best balance of reasoning and speed for local deployment.
*   **Decoupled Resolution**: By splitting extraction and resolution, the UI remains responsive even when the system is performing slow web searches for obscure foods.
*   **Environment-Aware Vision**: Recognizes that a "plate" at home differs from a "plate" at a restaurant, applying different weight heuristics to improve estimation accuracy.
