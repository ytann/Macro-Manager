# Sprint 6: Snappy UX & Reliable Extraction

## 1. Problem Statement
**Perceived Latency**: The current `/log` endpoint is a monolithic blocking call. If an item requires a web search, the frontend hangs for 30-60s, leading to connection timeouts and a "frozen" UX.
**Cache Inefficiency**: Strict string matching causes cache misses for near-identical terms (e.g., "Budhani Chips" vs "Budhani Potato Chips"), triggering unnecessary and slow web searches.

## 2. Proposed Solution

### A. Async Progress Pipeline (UX Overhaul)
Shift from a **Request-Response** model to a **Job-Status** model:
1. **`POST /log/start`**: LLM extracts items and weights -> Returns `meal_id` and `item_list` immediately (~3s).
2. **Background Resolution**: Server resolves nutrition for each item in parallel using `BackgroundTasks`.
3. **`GET /log/status/{meal_id}`**: Frontend polls this endpoint to see which items are resolved.
4. **Incremental UI**: The frontend displays items with individual loading spinners that turn into checkmarks as they resolve.

### B. Canonicalization Layer (Performance Overhaul)
Optimize the `FoodbankService` lookup to maximize L1/L2 cache hits:
1. **Fuzzy Matching**: Implement a similarity threshold (e.g., Levenshtein distance). If a name is >90% similar to a DB entry, treat it as a hit.
2. **Semantic Aliasing**: Enhance the alias lookup to handle common variations without triggering the LLM or Web Search.
3. **Confidence-Based Fallback**: 
   - **High Confidence** -> Instant Cache Hit.
   - **Medium Confidence** -> Quick LLM Verification (Faster than Web).
   - **Low Confidence** -> Authoritative Web Search.

## 3. Functional Requirements
- [ ] **API**: Implement `/log/start` and `/log/status/{meal_id}`.
- [ ] **Backend**: Decouple `ExtractionService.parse` into `extract_items()` and `resolve_nutrition()`.
- [ ] **Lookup**: Integrate fuzzy matching in `FoodbankService.get_nutrition_data`.
- [ ] **Frontend**: Update `frontend.py` to handle polling and per-item loading states.

## 4. QC & Testing Strategy (TDD)
Following `TESTING_INSTRUCTIONS.md`, we will use a **Red -> Fix -> Green** cycle.

### Layer 1: Element-wise (Unit)
- `tests/S6_unit_fuzzy_match.py`: Verify that "Budhani Chips" matches "Budhani Potato Chips" based on the similarity threshold.
- `tests/S6_unit_async_start.py`: Verify `/log/start` returns a `meal_id` and items within <5s.
- `tests/S6_unit_status_polling.py`: Verify status transitions from `pending` -> `partial` -> `completed`.

### Layer 2: Overall (Integration)
- `tests/S6_integration_pipeline.py`: Full flow test: `start` -> poll `status` -> verify `macros.db` is populated.
- `tests/S6_integration_cache_perf.py`: Compare resolution time for a "near-match" item before and after the canonicalization layer.

### Layer 3: Edge Cases
- `tests/S6_edge_empty_extraction.py`: Handle cases where the LLM finds no food items.
- `tests/S6_edge_web_failure.py`: Ensure background resolution doesn't crash if a web search fails; item should be marked as `unverified`.
- `tests/S6_edge_concurrency.py`: Stress test multiple concurrent logs to ensure the `asyncio.Semaphore` prevents server saturation.

## 5. Definition of Done
- [ ] All S6 tests pass (Green).
- [ ] User perceives "Instant" feedback after hitting Log.
- [ ] Web searches are only triggered for truly new/unknown items.
- [ ] No regressions in `tests/final_comprehensive_tests.py`.
