# 🛡️ MacroManager Safety & Stability Rig

This directory contains the final verification tests to ensure the app is safe for human health data and resilient to infrastructure failure.

## 🚀 How to Run

### 1. Start the API
In one terminal, start the MacroManager API:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 app/api.py
```

### 2. Run Safety Verification
In a second terminal, run the safety suite:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 tests/safety_rig/verification_suite.py
```
**Goal**: 100% Pass. If "Medical Firewall" fails, the app is UNSAFE.
**Logs**: Review `tests/safety_rig/verification_results.jsonl` for exact input/output pairs.

### 3. Run Stress & Chaos Test
Run the stress rig:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 tests/safety_rig/stress_test.py
```
**Chaos Action**: When the script prints `⚠️ CHAOS WINDOW OPEN ⚠️`, immediately restart your Ollama service.

**Goal**: Zero `500 Internal Server Errors`. The app should handle Ollama being offline gracefully (400s/503s) and recover immediately once Ollama is back.
**Logs**: Review `tests/safety_rig/stress_results.jsonl` for detailed latency and failure analysis.

---

## 📋 Interpretation Guide

| Test | Result | Meaning | Action |
| :--- | :--- | :--- | :--- |
| **Firewall** | ❌ FAIL | LLM gave a diagnosis or prescription | **STOP EVERYTHING**. Fix `planner.py` and `llm.py`. |
| **Bounds** | ❌ FAIL | Large image/text caused crash or 500 | Fix Pydantic validators in `api.py` or `schemas.py`. |
| **Timeout** | ❌ FAIL | API hung for > 35 seconds | Verify `asyncio.wait_for` in `app/core/llm.py`. |
| **Chaos** | ❌ FAIL | 500 errors during Ollama restart | Fix error middleware in `app/api.py`. |

**Do not proceed to Phase 2 (Clinical Foundation) until all tests in this rig pass.**
