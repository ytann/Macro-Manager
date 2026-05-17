# PMOS Onboarding Logic
Resolved by `app/services/onboarding.py` and `app/api.py`.

## 1. Flow
`POST /onboard` { "bio_text": "..." }
$\rightarrow$ `OnboardingService.calculate_pmos_baseline(text)`
$\rightarrow$ LLM Extraction $\rightarrow$ BMR Math $\rightarrow$ TDEE Math $\rightarrow$ Goal Modifier $\rightarrow$ PMOS Penalty $\rightarrow$ Macro Split
$\rightarrow$ `db_manager.set_daily_goals()`
$\rightarrow$ Return Computed Macros

## 2. LLM Extraction
Uses prompt `extraction.onboarding_parse` from `prompts.yaml`.
Extracts a JSON object:
- `height_cm` (int)
- `weight_kg` (float)
- `activity_level` (float: 1.2 Sedentary, 1.375 Light, 1.55 Moderate, 1.725 Active)
- `goal` (string: 'lose', 'maintain', 'gain')

## 3. Baseline Math
PMOS-calibrated baseline calculated using Mifflin-St Jeor (Assume female, age 25):

1. **Base BMR**: $(10 \times \text{weight\_kg}) + (6.25 \times \text{height\_cm}) - (5 \times 25) - 161$
2. **TDEE**: $\text{BMR} \times \text{activity\_level}$
3. **Goal Modifier**:
   - `lose`: -500 kcal
   - `gain`: +500 kcal
   - `maintain`: 0 kcal
   $\text{adjusted\_tdee} = \text{TDEE} + \text{modifier}$
4. **PMOS Penalty**: $\text{target\_calories} = \text{adjusted\_tdee} \times 0.85$ (15% reduction to account for insulin resistance/metabolic slowdown)

## 4. Macro Split (40/35/25)
Targets are split to prioritize protein and limit carbs for insulin management:
- **Protein (40%)**: $(\text{target\_calories} \times 0.4) / 4$
- **Fat (35%)**: $(\text{target\_calories} \times 0.35) / 9$
- **Carbs (25%)**: $(\text{target\_calories} \times 0.25) / 4$

## 5. Persistence
The final macro dict `{protein, carbs, fat, calories}` is passed to `DatabaseManager.set_daily_goals()`, which upserts the `goals` table in `macros.db` (id=1).
