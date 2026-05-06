1: FastAPI, Streamlit, SQLite (FTS5 Foodbank), LiteLLM (Model: llama3.1:latest).
2: Parser: Shape-agnostic logic extracting food lists. Implements a Two-Pass Extraction Pipeline: Initial Extraction -> Verification Guardrail (check for missed items) -> Deduplication/Cleanup. Deconstructs complex dishes into base ingredients using a recipe-lookup-and-learn system. Implements a "Reasoning & Verification Loop" where recipes are first generated with reasoning and then cross-verified by a second LLM pass to eliminate hallucinations.
3: Database: SQLite with FTS5 for alias-based food search. Implements schema migration for sub-macro columns. Implements "Learning Mode" using DuckDuckGo web search fallback for base foods and a "Recipe Store" for complex meals to ensure high-precision macro calculation.
4: Summary: Daily totals calculated using SQLite `date('now')` to ensure synchronization with UI.
5: Frontend: Streamlit interface with Big Three metrics and secondary sub-macro layout.
