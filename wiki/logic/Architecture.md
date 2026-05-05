FastAPI, Streamlit, SQLite (FTS5 Foodbank), LiteLLM.
Parser: Shape-agnostic logic extracting food lists from 'items', 'data', or 'response' keys; cleans markdown backticks; deconstructs complex dishes into base ingredients using a recipe-lookup-and-learn system.
Database: SQLite with FTS5 for alias-based food search. Implements schema migration for sub-macro columns. Implements "Learning Mode" for base foods and a "Recipe Store" for complex meals to ensure high-precision macro calculation.
Summary: Daily totals calculated using SQLite `date('now')` to ensure synchronization with UI.
Frontend: Streamlit interface with Big Three metrics and secondary sub-macro layout.
