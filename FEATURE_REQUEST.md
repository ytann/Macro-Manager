# Feature Request Template

Use this template to propose and track new features in MacroManager. This ensures a consistent development loop: **Postulate $\rightarrow$ Test-First $\rightarrow$ Implement $\rightarrow$ Verify.**

---

## 1. Feature Overview
- **Title**: [Feature Name]
- **Description**: [What is this feature? Why is it needed?]
- **User Story**: "As a [user], I want to [action] so that [outcome]."

## 2. Technical Design (Postulation)
### 2.1 Architecture Changes
- **Persistence**: [Does this require new DB tables or column updates? Specify the DB (foodbank vs macros)]
- **API**: [What new endpoints are needed? (Method, Path, Request/Response schema)]
- **Frontend**: [Where does this appear in the UI? What components are added/changed?]

### 2.2 Impacted Files
| Layer | File Path | Change Description |
| :--- | :--- | :--- |
| **Schema** | `app/schemas/food_schemas.py` | [e.g., Add NewModel] |
| **Database**| `app/services/database.py` | [e.g., New table, new helper method] |
| **API** | `app/api.py` | [e.g., Add POST/GET endpoint] |
| **Frontend**| `app/frontend.py` | [e.g., Add st.expander or st.button] |

### 2.3 Data Flow
`User Action` $\rightarrow$ `Frontend` $\rightarrow$ `API` $\rightarrow$ `Service` $\rightarrow$ `Database` $\rightarrow$ `UI Response`

---

## 3. Verification Strategy (Test-First)
Before implementation, define the "Green" state. Tests must follow the naming convention: `tests/ISSUE_[NAME]_[level]_[description].py`.

### 3.1 Unit Tests
- [ ] **Test [Component]**: [What specifically is being tested? e.g., DB method return value]
- [ ] **Test [Component]**: ...

### 3.2 Integration Tests
- [ ] **Test [Flow]**: [e.g., API request $\rightarrow$ DB update $\rightarrow$ Summary endpoint reflects change]
- [ ] **Test [Flow]**: ...

### 3.3 Edge Cases
- [ ] **Validation**: [e.g., Negative numbers, null values, extremely large inputs]
- [ ] **Failure Modes**: [e.g., Database connection timeout, invalid API payload]

---

## 4. Implementation Checklist
- [ ] **TDD Phase**: Write all tests $\rightarrow$ Confirm they fail (Red).
- [ ] **Code Phase**: Implement changes in the impacted files.
- [ ] **Linting**: Run `ruff check .` and resolve all errors.
- [ ] **Verify Phase**: Run the specific `ISSUE_[NAME]` tests $\rightarrow$ Confirm they pass (Green).
- [ ] **Regression**: Run comprehensive test suites to ensure no breakage.
