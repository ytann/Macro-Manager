# 📖 Project Details: MacroManager

## 1. Introduction
MacroManager is an intelligent nutrition tracking system that bridges the gap between natural language food logging and precise nutritional analysis. The system is designed to handle the ambiguity of human speech (e.g., "a plate of poha") and the complexity of regional cuisines, ensuring that every calorie is accounted for accurately.

---

## 2. High-Level Design (HLD)

### 2.1 Architecture Overview
The system follows a decoupled **Client-Server Architecture**:
- **Frontend (Streamlit)**: Provides a user-friendly interface for logging food and visualizing daily progress.
- **Backend (FastAPI)**: Orchestrates the data flow between the LLM, the nutrition database, and the user logs.
- **Nutritional Intelligence (Llama 3.1 + Foodbank)**: A hybrid system that combines a local FTS5-powered database with an LLM-driven web-search agent.
- **Persistence Layer (SQLite)**: Two distinct databases—one for static/learned food data (`foodbank.db`) and one for user meal logs (`macros.db`).

### 2.2 Data Flow
1. **User Input** $\rightarrow$ Natural language text (e.g., "2 eggs and a bowl of dal").
2. **Extraction Pipeline** $\rightarrow$ 
    - Pass 1: Initial Item/Weight Extraction.
    - Pass 2: Verification Guardrail (check for missed items).
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

#### A. `DatabaseManager` (Singleton)
- **Purpose**: Centralizes all SQLite interactions.
- **Key Logic**: 
    - Uses **FTS5 (Full-Text Search)** for the foodbank to allow fast, alias-based lookups (e.g., searching 'chawal' finds 'Rice').
    - Implements automated schema migration to ensure the database evolves without data loss.

#### B. `FoodbankService`
- **Streamlined Intelligence**: Implements a single-entry `get_nutrition_data` method that handles the entire lifecycle from DB lookup to authoritative web search and persistence.
- **Async Core**: Fully refactored to use `asyncio` and `httpx`, allowing non-blocking network requests and database operations via `to_thread`.
- **Recipe Store**: Saves and retrieves JSON-based recipes for complex dishes to ensure consistency in expansion.
- **Learning Mode**: Automatically persists newly discovered foods to the database to reduce future LLM calls.

#### C. `ExtractionService`
- **Two-Pass Pipeline**: Uses a "Check and Balance" system. The first pass extracts; the second pass (Verification Guardrail) explicitly asks the LLM: *"Did you miss anything?"*
- **Parallel Execution**: Processes all base ingredients concurrently using `asyncio.gather`, minimizing API latency for meals with multiple items.
- **Density-Aware Estimation**: Instead of static weights, the prompt instructs the LLM to consider the nature of the food (e.g., Sev Puri vs. Rice) when estimating grams for "plates" or "bowls".
- **Deduplication**: a custom logic filter that removes non-food terms (like "plate") and overlapping names.

#### D. `Pydantic Schemas`
- Enforces strict data types and constraints (e.g., `ge=0` for macros) to prevent negative values or `NoneType` errors.

---

## 4. Functional Specifications

### 4.1 Key Features
| Feature | Description | Implementation |
| :--- | :--- | :--- |
| **Natural Language Parsing** | Converts "2 eggs" $\rightarrow$ `FoodItem(name="Egg", grams=100)` | Llama 3.1 + Two-Pass Pipeline |
| **Regional Support** | Handles complex dishes like Misal Pav or Puran Poli | Recipe Expansion + SoT Web Search |
| **Caloric Guardrail** | Prevents macro-calorie mismatch | Atwater Formula: $P*4 + C*4 + F*9$ |
| **Verified Database** | Marks data as `verified` once confirmed via web | `verified` flag in SQLite |
| **Deterministic Output** | Same input always yields same output | Temperature = 0.0 |

### 4.2 API Endpoints
- `POST /log`: Parses text, calculates macros, and saves the meal.
- `GET /summary`: Returns aggregated totals for the day and daily goals.
- `GET /meals`: Lists all detailed food items logged today.
- `DELETE /clear`: Resets daily progress.

---

## 5. Design Decisions & Trade-offs
- **SQLite FTS5 vs. Standard SQL**: Chosen for superior alias searching and performance with nutrition datasets.
- **Externalized Prompts**: Prompts are stored in `prompts.yaml` to allow non-developers to tune the AI's behavior without modifying Python code.
- **Local LLM (Ollama)**: Prioritizes privacy and offline capability over cloud-based APIs.
- **Two-Pass vs. Single-Pass**: Single-pass extraction often misses items in long lists. The verification pass adds a small latency but significantly increases recall.
