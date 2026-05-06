# Food Identification & Learning Logic

This page describes the multi-stage process used by the `app/parser.py` to identify foods and learn new ones from the LLM.

## 1. Identification Flow
For every item extracted from the user's log:
1. **DB Lookup**: Search `foodbank.db` for an exact name match or an alias match using FTS5.
2. **Complex Dish Analysis**: If not found, ask the LLM if the item is a complex dish (e.g., "Poha", "Pasta").
3. **Recipe Generation & Verification**:
   - **Step A (Generation)**: LLM provides a recipe (base ingredients + weights) along with a **Reasoning** field to prevent hallucinations.
   - **Step B (Verification)**: A second LLM call verifies the proposed recipe against traditional standards. If an error is detected (e.g., "rice flour" instead of "flattened rice"), it is corrected here.
   - **Step C (Persistence)**: The verified recipe is stored in the `recipes` table.
4. **Ingredient Decomposition**: The dish is broken down into its verified base ingredients, each processed recursively through this flow.

## 2. Learning New Base Ingredients
When a base ingredient (single item) is not in the database:
1. **Authoritative Search (Source of Truth)**: The system performs a web search (via DuckDuckGo) for the item's nutrition facts. A validator LLM then extracts the most authoritative 100g macros from the HTML, prioritizing government and scientific sources.
2. **Pydantic Validation**: The output is validated against the `Macros` and `SubMacros` schemas.
3. **Persistence**: The validated data is saved to the `foods` table for future use.

## 3. Anti-Hallucination Measures
- **Reasoning-First**: Forcing the LLM to explain the composition before listing ingredients.
- **Few-Shot Examples**: Providing gold-standard examples of complex dishes in the prompt.
- **Verification Loop**: A mandatory second-pass check to catch common LLM mistakes.
- **Persona Prompting**: Using "expert nutrition database" to improve macro accuracy.
