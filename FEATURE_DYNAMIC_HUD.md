# Feature Request: Dynamic Macro HUD Filling

## 1. Feature Overview
- **Title**: Dynamic Macro HUD Filling
- **Description**: Implement a visual filling effect in the Macro HUD cards based on the proportion of consumed macros vs goals.
- **User Story**: "As a user, I want to see a visual representation of how close I am to my macro goals directly on the HUD cards, with alerts when I exceed them."

## 2. Technical Design (Postulation)
### 2.1 Architecture Changes
- **Persistence**: None.
- **API**: None.
- **Frontend**: Update `render_macro_hud` in `app/frontend.py`.

### 2.2 Impacted Files
| Layer | File Path | Change Description |
| :--- | :--- | :--- |
| **Frontend**| `app/frontend.py` | Update `render_macro_hud` CSS and HTML logic to include `conic-gradient` fill and alert icons. |

### 2.3 Data Flow
`consumed` & `goals` $\rightarrow$ Calculate `ratio = consumed/goal` $\rightarrow$ Generate `conic-gradient(from 180deg, color ratio%, transparent 0%)` $\rightarrow$ Inject into HTML $\rightarrow$ Render in Streamlit.

## 3. Verification Strategy (Test-First)
### 3.1 Unit Tests
- [ ] **Test Fill Logic**: Verify that ratio $0.5$ results in $50\%$ fill in CSS.
- [ ] **Test Empty State**: Verify that 0 consumed macros result in transparent/no fill.
- [ ] **Test Protein Alert**: Verify that Protein $> 1.0$ adds a green exclamation mark.
- [ ] **Test Carb/Fat Alert**: Verify that Carbs/Fat $> 1.0$ adds a warning alert sign.
- [ ] **Test Clamp**: Verify that fill percentage does not exceed $100\%$ visually.

## 4. Implementation Checklist
- [ ] **TDD Phase**: Write `tests/ISSUE_DYNAMIC_HUD_unit.py` $\rightarrow$ Confirm they fail.
- [ ] **Code Phase**: Update `render_macro_hud` in `app/frontend.py`.
- [ ] **Linting**: Run `ruff check .`.
- [ ] **Verify Phase**: Run tests $\rightarrow$ Confirm they pass.
