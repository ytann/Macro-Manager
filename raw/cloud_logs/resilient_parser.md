# Resilient Parser Logic
Success: The LLM returned a nested dict `{"items": [...]}` instead of a list. The parser successfully dynamically extracted it. 
Success: 'chickpeas' was missing from DB. Instead of crashing (500/400 error), the system warned, skipped, and logged the rest.
Rule: ALL future parsers must be shape-agnostic (check for 'items', 'data', 'response') and must fail gracefully on missing data without crashing the main API loop.
