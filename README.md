# 📓 MacroManager

AI-powered nutrition tracking specialized for **PMOS (prev. PCOS)/PCOD** management. It transforms natural language food logs into precise macro-nutrient data using a multi-pass extraction pipeline and a clinical knowledge base.

## ✨ Key Features

- **📓 Plain Notebook UI**: High-fidelity, emotionally intimate aesthetic (Courier Prime typography, grid-paper background) designed to reduce cognitive load.
- **🎯 PMOS Calibration**: One-shot onboarding that extracts biometrics from free-text bios and calculates PMOS-calibrated macro targets (including a 15% metabolic penalty).
- **📝 Intelligent Food Journal**: 
  - **Inline Editing**: Update quantities directly in the journal; macros scale proportionally in real-time.
  - **Timezone Alignment**: Server-side `localtime` synchronization to prevent "ghost entries" and date mismatches.
- **📷 Vision Extraction**: Multimodal food analysis with environment-aware portion estimation (`Home` vs `Wild`).
- **🩺 Clinical Copilot**: AI-driven dietary guidance primed with PMOS metabolic context, protected by a **Medical Firewall** to ensure safety.
- **🔄 Sovereign Memory**: A personalized dietary glossary that remembers your specific utensil sizes and food preferences.
- **📡 Offline-Ready**: Async sync queue with heartbeat lifecycle for seamless logging in low-connectivity areas.

## 🚀 Quick Start

### 1. Prerequisites
- **Ollama** installed and running.
- Model pulled: `ollama pull gemma4:e2b`

### 2. Installation
```bash
pip install -r requirements.txt
```

### 3. Running the App
Open two terminal windows:

**Terminal 1: Backend API**
```bash
export PYTHONPATH=$PYTHONPATH:.
python -m app.api
```

**Terminal 2: Frontend Dashboard**
```bash
export PYTHONPATH=$PYTHONPATH:.
streamlit run app/frontend.py
```

## 📱 Mobile Access via Tailscale (Recommended)

Since MacroManager is designed for mobile use, use **Tailscale** to access your local server securely from your phone without port forwarding.

1. **Install Tailscale** on your host machine and your mobile device.
2. **Login** to the same Tailscale account on both.
3. **Find your Host IP**: Get the Tailscale IP of your computer (e.g., `100.x.y.z`).
4. **Access on Mobile**: 
   - Open your mobile browser.
   - Navigate to `http://100.x.y.z:8501` (Streamlit default port).
5. **Backend Sync**: Ensure the `API_URL` in `app/frontend.py` is set to your Tailscale IP if the frontend and backend are on different machines, or leave as `localhost` if accessed via a tunnel.

## 📂 Project Structure

```
MacroManager/
  app/
    api.py                    # FastAPI endpoints + heartbeat lifecycle
    frontend.py               # Streamlit dashboard (Notebook UI)
    core/
      config.py               # PMOS Clinical Constants
      llm.py                  # Global LLM concurrency control
    services/
      database.py             # SQLite FTS5 + meal persistence
      foodbank.py             # Nutrition resolution & L1 caching
      extraction.py           # Single-pass LLM parsing & Vision pipeline
      onboarding.py           # PMOS baseline calibration
    schemas/
      food_schemas.py         # Pydantic models for nutrition data
  prompts/
    prompts.yaml              # Externalized LLM prompts
  wiki/                       # Agent routing & Clinical Knowledge Base
    index.md                  # Agent Routing Table
    logic/                    # Architecture & Math specs
    pmos_nutrition/           # PMOS Clinical Knowledge Base
  ProjectDetails.md           # Full HLD/LLD documentation
  requirements.txt            # Project dependencies
```

## 🛠 API Reference

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/planner` | `POST` | Clinical Copilot: Route query $\rightarrow$ Knowledge $\rightarrow$ Dietary Plan |
| `/log/start` | `POST` | Fast item extraction $\rightarrow$ returns `meal_id` for async resolution |
| `/log/status/{id}` | `GET` | Poll resolution status (`processing` $\rightarrow$ `completed`) |
| `/vision-log` | `POST` | Multimodal extraction from image $\rightarrow$ Resolve $\rightarrow$ Save |
| `/onboard` | `POST` | Bio-text $\rightarrow$ Calculate PMOS targets $\rightarrow$ Save goals |
| `/summary` | `GET` | Daily aggregates + goals + weekly buffer |
| `/meals` | `GET` | Chronological meal retrieval for a specific date |
| `/goals` | `POST` | Manual update of macro targets |
