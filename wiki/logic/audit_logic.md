# Audit Logic - Implementation Steps

## Execution Order
Critical > High > Medium > Low

---

## Phase 1: Critical Fixes

### Fix #1: Race condition in `asyncio.gather`

**File:** `app/services/extraction.py`

**Step 1:** Remove shared mutable `state` dict and `parsed_items` list from concurrent mutation. Have `_process_base_ingredient` return its computed values instead of mutating shared state.

**Step 2:** Change `_process_base_ingredient` signature from:
```python
async def _process_base_ingredient(self, name, grams, state, parsed_items):
```
to return a tuple:
```python
async def _process_base_ingredient(self, name, grams) -> Optional[Tuple[Dict, FoodItem]]:
```
Returns `(macro_delta, food_item)` or `None` if no data.

**Step 3:** Rewrite the gather logic in `parse` to aggregate results after all tasks complete:
```python
results = await asyncio.gather(*tasks)
for result in results:
    if result is None:
        continue
    macro_delta, food_item = result
    state['p'] += macro_delta['p']
    state['c'] += macro_delta['c']
    state['f'] += macro_delta['f']
    state['cal'] += macro_delta['cal']
    parsed_items.append(food_item)
```

**Step 4:** Verify with `python3 -c "import asyncio; ..."` and ensure consistent totals across multiple runs.

---

### Fix #2: Database drops all data on startup

**File:** `app/services/database.py`

**Step 1:** Replace `DROP TABLE IF EXISTS foods` with `CREATE VIRTUAL TABLE IF NOT EXISTS`.

**Step 2:** Check if the table has zero rows before seeding:
```python
cursor.execute("SELECT COUNT(*) FROM foods")
count = cursor.fetchone()[0]
if count == 0:
    # Seed initial foods only if empty
    cursor.executemany("INSERT INTO foods VALUES (...)", foods)
```

**Step 3:** Verify by running twice - second run should preserve previously learned data:
```bash
python3 -c "from app.services.database import DatabaseManager; db = DatabaseManager()" 
sqlite3 foodbank.db "SELECT COUNT(*) FROM foods"
# Restart and check count is preserved
```

**[FIXED]** — Removed `DROP TABLE`, changed to `CREATE VIRTUAL TABLE IF NOT EXISTS`. Verified with `tests/ISSUE_DBDROP_unit_persist.py`.

---

### Fix #3: Missing recipe expansion

**File:** `app/services/extraction.py`

**Step 1:** Split `items_list` processing into recipe items and base ingredient items.

**Step 2:** For recipe items, fetch the recipe from foodbank, expand into ingredients, then process those. Maintain dish summaries.

**Step 3:** Sequential recipe processing (recipes depend on each other's ingredient state) and parallel base ingredient processing.

**Step 4:** Pseudocode:
```python
# Phase 1: Recipe expansion (sequential)
for item in items_list:
    recipe = await self.foodbank.get_recipe(item['name'])
    if recipe:
        # expand recipe, process ingredients, insert dish summary
    else:
        # defer to parallel phase
        base_items.append(item)

# Phase 2: Base ingredients (parallel)
results = []  # GUARD: prevents NameError when all items are recipes
if base_tasks:
    results = await asyncio.gather(*base_tasks)
for result in results:
    ...
```

**Step 5:** Verify with "1 plate pani puri" - should show `Pani Puri (Total)` and ingredient breakdown.

**[FIXED]** — `results = []` guard added before `if base_tasks:` block. Verified with `tests/ISSUE_NAMEERROR_unit_recipe.py`.

---

## Phase 2: High Priority Fixes

### Fix #6: Crash bug in `get_nutrition_data`

**File:** `app/services/foodbank.py`

**Step 1:** Change line 127 from:
```python
estimate_prompt = self.prompts['foodbank']['internal_estimate'].format(name=name)
```
to:
```python
estimate_prompt = self.prompts['internal_estimate'].format(name=name)
```

**Step 2:** Verify fallback path by simulating a network failure:
```bash
# Temporarily block duckduckgo, then test parse
```

---

### Fix #4: Clean up dead code

**Files to delete:** `app/parser.py`, `app/foodbank.py`, `app/database.py`

**Step 1:** Delete the three files:
```bash
rm app/parser.py app/foodbank.py app/database.py
```

**Step 2:** Check for any remaining imports of these modules:
```bash
grep -r "from app import parser\|from app import foodbank\|from app import database\|from app.parser\|from app.foodbank\|from app.database" --include="*.py"
```

**Step 3:** Update `scripts/ingest_csv.py` to import from `app.services.database` instead of `app.database`.

**Step 4:** Delete `__pycache__` directories to remove stale `.pyc` files:
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
```

---

### Fix #5: Add missing dependencies

**File:** `requirements.txt`

**Step 1:** Add `httpx` and `pyyaml`:
```
httpx
pyyaml
```

**Step 2:** Verify with:
```bash
pip install -r requirements.txt
```

---

## Phase 3: Medium Priority Fixes

### Fix #7: Deduplicate web requests

**File:** `app/services/foodbank.py`

**Step 1:** Move the DuckDuckGo HTML fetch into a shared `_fetch_web_data` method.

**Step 2:** Pass the same HTML to both `find_source_of_truth` and `search_web_for_food` in `get_nutrition_data`.

---

### Fix #8: Add `source_json` column

**File:** `app/services/database.py`

**Step 1:** Add `source_json UNINDEXED` to the FTS5 CREATE TABLE statement.

**Step 2:** Update `upsert_food` to accept and store `source_json`.

**Step 3:** Update `find_source_of_truth` to pass the `source` field to `upsert_food`.

---

### Fix #9: Externalize `find_source_of_truth` prompt

**File:** `prompts/prompts.yaml`

**Step 1:** Add `source_of_truth` key under `foodbank:`.

**Step 2:** Update `find_source_of_truth` to use `self.prompts['source_of_truth']`.

---

### Fix #10: Update wiki pages

**Files:** `wiki/logic/FoodLearning.md`, `wiki/logic/FoodLogSchema.md`, `wiki/logic/Architecture.md`, `wiki/index.md`

**Step 1:** Update `FoodLearning.md`:
- Remove reference to `app/parser.py`.
- Update to describe current `FoodbankService.get_nutrition_data` flow.
- Note that recipe expansion is handled in `ExtractionService.parse`.

**Step 2:** Update `FoodLogSchema.md` to match current `app/schemas/food_schemas.py`.

**Step 3:** Update `Architecture.md` to mention async pipeline, `asyncio.gather`, `httpx`.

**Step 4:** Add `audit_logic.md` entry to `wiki/index.md`.

---

### Fix #11: Remove singleton from DatabaseManager

**File:** `app/services/database.py`

**Step 1:** Remove `__new__` override.

**Step 2:** Add `reset=False` parameter to `__init__`:
```python
def __init__(self, reset=False):
    if reset:
        self._init_db()
```

**Step 3:** Update callers to use normal instantiation.

---

### Fix #12: Update `ingest_csv.py` schema

**File:** `scripts/ingest_csv.py`

**Step 1:** Add `verified` column to CREATE TABLE.

**Step 2:** Change import from `app.database` to `app.services.database` after deleting old `app/database.py`.

---

## Phase 4: Low Priority Fixes

### Fix #13: Add per-request cache
Add `self._cache = {}` in `ExtractionService._process_base_ingredient` or `FoodbankService.get_nutrition_data`.

### Fix #14: Reuse httpx client
Move `self.client = httpx.AsyncClient()` to `__init__` and reuse across methods.

### Fix #15: Move debug scripts
```bash
mkdir -p debug
mv final_comprehensive_tests.py verify_async.py get_poha_source.py debug/
```

### Fix #16: (Optional) Async frontend
Switch Streamlit frontend to `httpx` if async support matures.

### Fix #17: Remove empty directories
```bash
rmdir templates/ wiki/entities/
```

### Fix #18: Unify fiber return format
Standardize the return dict format across `find_source_of_truth`, `search_web_for_food`, and `internal_estimate` to all use flat keys: `{'calories', 'protein', 'carbs', 'fat', 'fiber'}`.