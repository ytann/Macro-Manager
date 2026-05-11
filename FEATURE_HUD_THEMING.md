# Feature Request: HUD Complementary Colors (Light/Dark Mode)

## 1. Feature Overview
- **Title**: HUD Complementary Colors
- **Description**: Ensure the Macro HUD is visually appealing and legible in both light and dark modes.
- **User Story**: "As a user, I want the HUD to adapt its colors when I switch my system or app theme, so that the text remains legible and the glass effect persists."

## 2. Technical Design (Postulation)
### 2.1 Architecture Changes
- **Persistence**: None.
- **API**: None.
- **Frontend**: Update `render_macro_hud` in `app/frontend.py` to use theme-aware CSS.

### 2.2 Impacted Files
| Layer | File Path | Change Description |
| :--- | :--- | :--- |
| **Frontend**| `app/frontend.py` | Introduce CSS variables for colors and a `@media (prefers-color-scheme: light)` block to override them. |

### 2.3 Data Flow
`Browser Theme` $\rightarrow$ `CSS Media Query` $\rightarrow$ `Update --text-color, --glass-border, --glass-shadow` $\rightarrow$ `Rendered HUD`.

## 3. Verification Strategy
- [ ] **Visual Check (Dark)**: Text is white, glass effect is subtle and dark-themed.
- [ ] **Visual Check (Light)**: Text is dark, glass effect is visible against a light background, colors are legible.
- [ ] **Contrast Check**: Ensure the contrast ratio between text and background meets accessibility standards (approx. 4.5:1).

## 4. Implementation Checklist
- [ ] **Code Phase**: Modify `render_macro_hud` CSS in `app/frontend.py`.
- [ ] **Verification**: Verify CSS logic for media queries.
