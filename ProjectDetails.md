# 📖 Project Details: MacroManager

## 1. Introduction
MacroManager is an intelligent nutrition tracking system designed specifically for PCOS/PCOD dietary management. It bridges the gap between natural language food logging and precise nutritional analysis. The system is designed to handle the ambiguity of human speech (e.g., "a plate of poha") and the complexity of regional cuisines, ensuring that every calorie is accounted for accurately. A one-shot onboarding flow extracts user biometrics from free-text bios and calculates PCOS-calibrated macro targets.

---

## 2. High-Level Design (HLD)

### 2.1 Architecture Overview
The system follows a decoupled **Client-Server Architecture**:
- **Frontend (Streamlit)**: Provides a high-fidelity interface for logging food and visualizing progress. Features an interactive 3D Glass HUD for macro tracking and integrated Voice-to-Log capabilities via the Web Speech API. Uses synchronous `httpx.Client` for reliable communication with the backend to prevent event-loop conflicts.
- **Backend (FastAPI)**: Orchestrates the data flow between the LLM, the nutrition database, the user logs, and the vision pipeline.
- **Nutritional Intelligence (Gemma 4 + Foodbank)**: A hybrid system that combines a local FTS5-powered database with an LLM-driven web-search agent.
- **Persistence Layer (SQLite)**: Two distinct databases-one for static/learned food data (`foodbank.db`) and one for user meal logs (`macros.db`).
- **Vision Pipeline (Gemma 4 multimodal)**: An encapsulated, decoupled module that extracts food items from images with environment-aware portion size estimation (Home vs. Wild).
- **Onboarding Engine**: LLM-driven attribute extraction from free-text bios, followed by deterministic PCOS-calibrated macro calculation (Mifflin-St Jeor BMR $\rightarrow$ TDEE $\rightarrow$ PCOS Penalty $\rightarrow$ Macro Split).

### 2.2 Data Flow
1. **User Input** $\rightarrow$ Natural language text (e.g., "2 eggs and a bowl of dal") OR image (base64 + environment flag).
2. **Extraction Pipeline** $\rightarrow$ 
    - Text Path (Two-Pass): Pass 1 $\rightarrow$ Initial Item/Weight Extraction. Pass 2 $\rightarrow$ Verification Guardrail.
    - Vision Path (Encapsulated): Pass 1 $\rightarrow$ Multimodal image analysis (Analysis $\rightarrow$ Extraction) with environment-aware portion estimation and optional user hints.
    - Convergence: Both paths produce a list of extracted items which are then processed by the Unified Resolver.
    - Cleanup: Deduplication and quantifier removal.
3. **Nutritional Resolution (Async Parallelized)** $\rightarrow$ 
    - **Parallel Lookup**: All extracted items are processed concurrently using `asyncio.gather`.
    - **Streamlined Logic**: Local DB Check $\rightarrow$ (if missing/unverified) $\rightarrow$ Authoritative Web Search $\rightarrow$ General Web Search $\rightarrow$ LLM Estimate $\rightarrow$ DB Upsert.
    - **Verification**: Items fetched authoritatively are marked as `verified=1` immediately.
4. **Caloric Validation** $\rightarrow$ Apply Atwater's formula to ensure calories match macros.
5. **Persistence** $\rightarrow$ Save result to `macros.db` and return summary to UI.

---

## 3. Low-Level Design (LLD)

### 3.1 Core Components

#### A. `DatabaseManager`
- **Purpose**: Centralizes all SQLite interactions.
- **Key Logic**: 
    - Uses **FTS5 (Full-Text Search)** for the foodbank to allow fast, alias-based lookups (e.g., searching 'chawal' finds 'Rice').
    - Implements automated schema migration to ensure the database evolves without data loss.
    - **Temporal Aggregation**: Provides weekly summaries for the current calendar week (Monday-Sunday).
    - **Standardized Seeding**: Maintains `DEFAULT_FOODS` matching the 13-column schema to ensure consistent initial nutrition data.

#### B. `FoodbankService`
- **Streamlined Intelligence**: Implements a single-entry `get_nutrition_data` method that handles the entire lifecycle from DB lookup to authoritative web search and persistence. All paths are standardized to return a flat macro dictionary.
- **L1 In-Memory Cache**: Utilizes a fast dictionary-based cache to store recently resolved food items, eliminating redundant DB and network calls for frequent foods.
- **Async Core**: Fully refactored to use `asyncio` and `httpx`, allowing non-blocking network requests and database operations via `to_thread`. Implements `close()` for graceful resource cleanup of the shared HTTP client.
- **Recipe Store**: Saves and retrieves JSON-based recipes for complex dishes to ensure consistency in expansion.
- **Learning Mode**: Automatically persists newly discovered foods to the database to reduce future LLM calls.
- **Consistent Seeding**: Uses a shared `DEFAULT_FOODS` constant to seed the database via `upsert_food`, preventing duplicate entries in the FTS5 table.

#### C. `ExtractionService`
- **Unified Resolver (`_resolve_and_build_log`)**: A centralized engine that takes a list of extracted items and a meal ID to build a complete `FoodLog`. It handles recipe expansion and nutrition resolution identically for both text and vision inputs, eliminating logic duplication.
- **Two-Pass Pipeline (Text)**: Uses a "Check and Balance" system. The first pass extracts; the second pass (Verification Guardrail) explicitly asks the LLM: *"Did you miss anything?"*
    - **Vision Extraction (Image)**: Implements a two-step reasoning process (Analysis $\rightarrow$ Extraction). The model first analyzes the image to confirm food presence and describes it in a 'reasoning' field before extracting specific items and weights. This prevents placeholders and improves identification accuracy. Supports `Home` (smaller portions) and `Wild` (restaurant-scale) environment rules, and utilizes optional `hint` strings to disambiguate items in the image.
- **Parallel Execution**: Processes all base ingredients concurrently using `asyncio.gather`, minimizing API latency for meals with multiple items.
- **Density-Aware Estimation**: Instead of static weights, the prompt instructs the LLM to consider the nature of the food (e.g., Sev Puri vs. Rice) when estimating grams for "plates" or "bowls".
- **Deduplication**: a custom logic filter that removes non-food terms (like "plate") and overlapping names.

#### D. `Pydantic Schemas`
- Enforces strict data types and constraints (e.g., `ge=0` for macros) to prevent negative values or `NoneType` errors.

#### E. `OnboardingService`
- **Purpose**: One-shot user onboarding — extracts physical attributes from a free-text bio dump and calculates optimized PCOS macro targets.
- **Key Logic**:
    - **LLM Extraction**: Sends user bio text to Gemma 4 with `onboarding_parse` prompt; parses JSON for `height_cm`, `weight_kg`, `activity_level`, `goal`.
    - **BMR (Mifflin-St Jeor, Female)**: $(10 \times \text{weight\_kg}) + (6.25 \times \text{height\_cm}) - (5 \times 25) - 161$ (assumes age 25).
    - **TDEE**: $\text{BMR} \times \text{activity\_level}$ where activity_level = 1.2 (sedentary), 1.375 (light), 1.55 (moderate), 1.725 (active).
    - **Goal Modifier**: $\text{lose} = -500$, $\text{maintain} = 0$, $\text{gain} = +500$ applied to TDEE.
    - **PCOS Penalty**: $\text{target\_calories} = \text{adjusted\_tdee} \times 0.85$ (15% metabolic reduction for PCOS context).
    - **Macro Split (40/35/25)**: Protein = $(\text{target\_cals} \times 0.4) / 4$, Fat = $(\text{target\_cals} \times 0.35) / 9$, Carbs = $(\text{target\_cals} \times 0.25) / 4$.
    - **Persistence**: Returns `{protein, carbs, fat, calories}` dict; endpoint writes to `goals` table via `DatabaseManager.set_daily_goals()`.

---

## 4. Functional Specifications

### 4.2 Vision UI Integration (Implemented)
- **Camera Interface**: Integrated `st.camera_input` in the Streamlit frontend.
- **Environment Context**: Added `Home` vs `Wild` toggle to influence portion size estimation.
- **Real-time Feedback**: Implemented loading spinners and success notifications upon meal extraction.
- **Frontend-Backend Link**: Created `app/utils/vision_client.py` to handle the encoding and transmission of image data to the `/vision-log` endpoint.
| Feature | Description | Implementation |
| :--- | :--- | :--- |
| **Natural Language Parsing** | Converts "2 eggs" $\rightarrow$ `FoodItem(name="Egg", grams=100)` | Gemma 4 + Two-Pass Pipeline |
| **Vision-Based Logging** | Extracts food items from meal images with environment-aware portions | Gemma 4 Multimodal + Home/Wild Rules |
| **Regional Support** | Handles complex dishes like Misal Pav or Puran Poli | Recipe Expansion + SoT Web Search |
| **Caloric Guardrail** | Prevents macro-calorie mismatch | Atwater Formula: $P*4 + C*4 + F*9$ |
| **Verified Database** | Marks data as `verified` once confirmed via web | `verified` flag in SQLite |
| **Deterministic Output** | Same input always yields same output | Temperature = 0.0 |
| **Interactive Macro HUD** | 3D flip-cards showing primary macros and sub-macros (Fiber, Sugar, Sat Fat) | Custom Glass CSS/HTML + Streamlit Components |
| **Voice-to-Log** | Hands-free food logging via voice recording $\rightarrow$ text $\rightarrow$ API | Web Speech API $\rightarrow$ Query Params $\rightarrow$ `/log` |

### 4.2 API Endpoints
- `POST /log`: Parses text, calculates macros, and saves the meal.
- `POST /vision-log`: Extracts food from a base64-encoded image with environment context (`Home`/`Wild`) and optional user hints, resolves nutrition via the Unified Resolver, and saves the meal.
- `POST /onboard`: Accepts `{bio_text: str}`, calls `OnboardingService.calculate_pcos_baseline()` to extract attributes and compute PCOS-calibrated macros, persists to `goals` table, returns computed macros.
- `GET /summary`: Returns aggregated totals for the day, daily goals, and a static calendar week summary.
- `POST /goals`: Updates user-defined macro targets.
- `GET /meals`: Lists all detailed food items logged today.
- `DELETE /clear`: Resets daily progress (Async).

---

## 5. Design Decisions & Trade-offs
- **SQLite FTS5 vs. Standard SQL**: Chosen for superior alias searching and performance with nutrition datasets.
- **Externalized Prompts**: Prompts are stored in `prompts.yaml` to allow non-developers to tune the AI's behavior without modifying Python code.
- **Local LLM (Ollama)**: Prioritizes privacy and offline capability over cloud-based APIs. Uses `gemma4:e2b` for both text extraction and multimodal vision analysis.
- **Two-Pass vs. Single-Pass**: Single-pass extraction often misses items in long lists. The verification pass adds a small latency but significantly increases recall.
- **Home vs. Wild Environment Rules**: Vision extraction uses environment-specific portion size heuristics (Home: ~250-500g plates; Wild: ~300-600g plates) to improve accuracy for home-cooked vs. restaurant meals.
