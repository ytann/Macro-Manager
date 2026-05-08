# Testing Instructions for Audit Fixes

## Objective
To systematically resolve all pending issues in `audit_logs.md` by creating a "Red-Green" testing cycle. Each issue must have isolated tests that fail on the current codebase and pass only after the fix is implemented.

## 🛠 Testing Strategy

### 1. Layered Approach
Each issue is broken down into three levels of verification:
- **Element-wise (Unit):** Tests the smallest possible unit of failure (e.g., checking for a specific column in a table or a specific import in a file).
- **Overall (Integration):** Tests the complete flow from input to output (e.g., parsing a meal and checking if the DB state is correct).
- **Edge Cases:** Tests boundary conditions, failure modes, and malformed inputs (e.g., network timeouts, null values, or weird food names).

### 2. Isolation & Naming
To prevent interference and allow easy tracking, tests are completely isolated.
**Naming Convention:** `tests/[issue_id]_[level]_[description].py`
- `ISSUE_DDG` -> `tests/ddg_...`
- `ISSUE_SOURCE` -> `tests/source_...`
- etc.

### 3. Execution Workflow
1. **Red Phase:** Run the test $\rightarrow$ Confirm failure (Issue verified).
2. **Fix Phase:** Implement the code change.
3. **Green Phase:** Run the test $\rightarrow$ Confirm success (Issue resolved).
4. **Regression Phase:** Run `tests/final_comprehensive_tests.py` to ensure no existing features were broken.

## Test Mapping
Refer to the detailed test plan provided in the chat history for the specific mapping of issues to test files.
