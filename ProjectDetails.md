# 📖 Project Details: MacroManager

## 1. Introduction
MacroManager is an intelligent nutrition tracking system that bridges the gap between natural language food logging and precise nutritional analysis. The system is designed to handle the ambiguity of human speech (e.g., "a plate of poha") and the complexity of regional cuisines, ensuring that every calorie is accounted for accurately.

---

## 2. High-Level Design (HLD)

### 2.1 Architecture Overview
The system follows a decoupled **Client-Server Architecture**:
- **Frontend (Streamlit)**: Provides a high-fidelity interface for logging food and visualizing progress. Features an interactive 3D Glass HUD for macro tracking and integrated Voice-to-Log capabilities via the Web Speech API. Uses synchronous `httpx.Client` for reliable communication with the backend to prevent event-loop conflicts.
- **Backend (FastAPI)**: Orchestrates the data flow between the LLM, the nutrition database, the user logs, and the vision pipeline.
- **Nutritional Intelligence (Gemma 4 + Foodbank)**: A hybrid system that combines a local FTS5-powered database with an LLM-driven web-search agent.
- **Persistence Layer (SQLite)**: Two distinct databases-one for static/learned food data (`foodbank.db`) and one for user meal logs (`macros.db`).
- **Vision Pipeline (Gemma 4 multimodal)**: An encapsulated, decoupled module that extracts food items from images with environment-aware portion size estimation (Home vs. Wild).

### 2.2 Data Flow
1. **User Input** $\rightarrow$ Natural language text (e.g., "2 eggs and a bowl of dal") OR image (base64 + environment flag).
2. **Extraction Pipeline** $\rightarrow$ 
    - Text Path (Two-Pass): Pass 1 $\rightarrow$ Initial Item/Weight Extraction. Pass 2 $\rightarrow$ Verification Guardrail.
    - Vision Path (Encapsulated): Pass 1 $\rightarrow$ Multimodal image analysis with environment-aware portion estimation.
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
    - **Temporal Aggregation**: Provides weekly summaries via specialized SQL aggregation over the last 7 days.
    - **Standardized Seeding**: Maintains `DEFAULT_FOODS` as a central source of truth for initial nutrition data.

#### B. `FoodbankService`
- **Streamlined Intelligence**: Implements a single-entry `get_nutrition_data` method that handles the entire lifecycle from DB lookup to authoritative web search and persistence. All paths are standardized to return a flat macro dictionary.
- **L1 In-Memory Cache**: Utilizes a fast dictionary-based cache to store recently resolved food items, eliminating redundant DB and network calls for frequent foods.
- **Async Core**: Fully refactored to use `asyncio` and `httpx`, allowing non-blocking network requests and database operations via `to_thread`. Implements `close()` for graceful resource cleanup of the shared HTTP client.
- **Recipe Store**: Saves and retrieves JSON-based recipes for complex dishes to ensure consistency in expansion.
- **Learning Mode**: Automatically persists newly discovered foods to the database to reduce future LLM calls.
- **Consistent Seeding**: Uses a shared `DEFAULT_FOODS` constant to seed the database via `upsert_food`, preventing duplicate entries in the FTS5 table.

#### C. `ExtractionService`
- **Two-Pass Pipeline (Text)**: Uses a "Check and Balance" system. The first pass extracts; the second pass (Verification Guardrail) explicitly asks the LLM: *"Did you miss anything?"*
- **Vision Extraction (Image)**: Standalone `extract_from_image(base64_image, environment)` method formats a multimodal payload (text + image) for `gemma4:e2b`, returning `[{name, grams}]` items. Supports `Home` (smaller portions) and `Wild` (restaurant-scale) environment rules.
- **Parallel Execution**: Processes all base ingredients concurrently using `asyncio.gather`, minimizing API latency for meals with multiple items.
- **Density-Aware Estimation**: Instead of static weights, the prompt instructs the LLM to consider the nature of the food (e.g., Sev Puri vs. Rice) when estimating grams for "plates" or "bowls".
- **Deduplication**: a custom logic filter that removes non-food terms (like "plate") and overlapping names.

#### D. `Pydantic Schemas`
- Enforces strict data types and constraints (e.g., `ge=0` for macros) to prevent negative values or `NoneType` errors.

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
- `POST /vision-log`: Extracts food from a base64-encoded image with environment context (`Home`/`Wild`), resolves nutrition, and saves the meal.
- `GET /summary`: Returns aggregated totals for the day, daily goals, and a 7-day rolling weekly summary.
- `POST /goals`: Updates user-defined macro targets.
- `GET /meals`: Lists all detailed food items logged today.
- `DELETE /clear`: Resets daily progress.

---

## 5. Design Decisions & Trade-offs
- **SQLite FTS5 vs. Standard SQL**: Chosen for superior alias searching and performance with nutrition datasets.
- **Externalized Prompts**: Prompts are stored in `prompts.yaml` to allow non-developers to tune the AI's behavior without modifying Python code.
- **Local LLM (Ollama)**: Prioritizes privacy and offline capability over cloud-based APIs. Uses `gemma4:e2b` for both text extraction and multimodal vision analysis.
- **Two-Pass vs. Single-Pass**: Single-pass extraction often misses items in long lists. The verification pass adds a small latency but significantly increases recall.
- **Home vs. Wild Environment Rules**: Vision extraction uses environment-specific portion size heuristics (Home: ~250-500g plates; Wild: ~300-600g plates) to improve accuracy for home-cooked vs. restaurant meals.
