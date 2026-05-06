# 🥗 MacroManager
 
MacroManager is a professional, AI-powered nutrition tracking system designed to transform messy, natural language food logs into precise macro-nutrient data. It utilizes a sophisticated multi-pass extraction pipeline and an authoritative "Source of Truth" learning system to ensure high-precision tracking.
 
## 🛠️ Overall Flow
`User Input` $\rightarrow$ `Two-Pass Extraction` $\rightarrow$ `Parallel Nutrition Resolution (Async)` $\rightarrow$ `Authoritative Web Search` $\rightarrow$ `Atwater Guardrail` $\rightarrow$ `Persistence` $\rightarrow$ `UI Dashboard`
 
## 🚀 Quick Start
 
### 1. Prerequisites
- **Ollama**: Ensure Ollama is installed and running.
- **Model**: Pull the required model: `ollama pull llama3.1:latest`.
 
### 2. Installation
```bash
pip install -r requirements.txt
```
 
### 3. Running the System
**Start the Backend API:**
```bash
python app/api.py
```
 
**Start the Frontend Dashboard:**
```bash
streamlit run app/frontend.py
```
 
## 🌟 Key Features
- **Async Parallel Processing**: All food items in a meal are resolved concurrently using `asyncio`, drastically reducing response times.
- **Two-Pass Extraction**: Uses an initial extraction pass followed by a **Verification Guardrail** to ensure no food items are missed.
- **Food-Aware Volume Estimation**: Estimates weights based on food density (e.g., distinguishing the weight of a 'plate' of rice vs. a 'plate' of sev puri).
- **Source of Truth (SoT) Learning**: Automatically validates and persists authoritative nutrition data from the web, marking items as `verified`.
- **Recipe Expansion**: Deconstructs complex regional dishes into base ingredients for mathematical precision.
- **Caloric Guardrails**: Automatically corrects calorie counts using the Atwater system to ensure macros and calories are consistent.
- **Deterministic Logic**: Fixed temperature settings ensure consistent outputs for the same input.
 
## 📂 Project Structure
- `app/core/`: Centralized configuration and constants.
- `app/services/`: Core business logic (Database, Extraction, Foodbank).
- `app/schemas/`: Pydantic models for data validation.
- `app/api/`: FastAPI endpoints.
- `app/ui/`: Streamlit frontend logic.
- `prompts/`: Externalized LLM prompts in YAML format.
- `tests/`: Comprehensive validation suite.
- `wiki/`: Detailed QA rules and logic documentation.
 
For a deep dive into the design, architecture, and implementation details, please refer to [ProjectDetails.md](./ProjectDetails.md).

