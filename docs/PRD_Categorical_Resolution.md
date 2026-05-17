# PRD: Categorical Food Resolution System

## 1. Problem Statement
The current food resolution system uses a "flat search" across the entire `foodbank.db`, followed by LLM-based verification. This has two major drawbacks:
- **High Latency**: Searching thousands of entries and making an LLM call for fuzzy matches is slow, leading to a poor user experience.
- **Low Precision**: The broad search space increases the risk of semantic "hallucinations" (e.g., "Saag Chicken" being matched with "Palak Saag"), where ingredients are similar but the dish is fundamentally different.

## 2. Proposed Solution: The Categorical Funnel
We will implement a "Categorical Funnel" to drastically reduce the search space *before* fuzzy matching. This shifts the architecture from a slow, broad search to a rapid, filtered one.

### 2.1. Taxonomy
The `foods` table will be augmented with a `category` column based on the following 10-class taxonomy:
1.  **Poultry**: Chicken, Turkey, Duck.
2.  **Red Meat**: Mutton, Lamb, Beef, Gosht.
3.  **Seafood**: Fish, Prawns, Shrimp, Crab, Lobster.
4.  **Egg**: Whole egg, Egg whites.
5.  **Pork**: Bacon, Ham, Sausage.
6.  **Dairy/Paneer**: Paneer, Cheese, Curd.
7.  **Soya/Tofu**: Soya chunks, Tofu, Tempeh.
8.  **Green Veggies**: Spinach, Saag, Broccoli, Beans, etc.
9.  **Starch/Breads**: Roti, Naan, Rice, Pasta.
10. **Other/Misc**: Everything else (fallback category).

### 2.2. The New Resolution Path
The query resolution logic will be updated to follow a tiered, "fast-path" approach:
1.  **Identify Category**: The user's query is first analyzed to extract a category based on keywords (e.g., "gosht" -> "Red Meat").
2.  **Category-Locked FTS Search**: The FTS5 search is executed *only* within the identified category. This reduces the search space by an order of magnitude.
3.  **Strict Fuzzy Match**: A high-confidence fuzzy match (Levenshtein distance) is performed on the small, filtered candidate set.
4.  **LLM Fallback**: If and only if the fast-path fails to yield a high-confidence match, the system falls back to the existing LLM verifier for a deeper semantic analysis.

## 3. Success Metrics
- **Performance**: Local resolution latency must be < 200ms for all "fast-path" queries.
- **Precision**: The system must achieve 100% accuracy on cross-category boundary tests (e.g., "Chicken Saag" vs "Paneer Saag").
- **Efficiency**: Reduce LLM token consumption for fuzzy matching by at least 80%.
