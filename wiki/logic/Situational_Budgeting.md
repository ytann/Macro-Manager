# Situational Budgeting & Macronutrient Balancing

## Goal
Ensure that meal suggestions are not just "mathematically possible" based on remaining macros, but are "situationally appropriate" based on the time of day and current daily progress.

## 1. Daily Budget Distribution
The system distributes the total daily allowance across four key meal windows to maintain stable insulin levels and energy.

| Meal Type | Target Allocation | Primary Goal |
| :--- | :--- | :--- |
| **Breakfast** | 25-30% | Metabolic kickstart, insulin stability |
| **Lunch** | 30-35% | Sustained energy, peak protein intake |
| **Snacks** | 10-15% | Bridge gaps, prevent extreme hunger |
| **Dinner** | 25-30% | Recovery, night-time insulin management |

## 2. Counter-Balancing Algorithm
The Clinical Copilot uses a "Counter-Balance" approach rather than a simple subtraction.

### The Logic:
1. **Target Calculation**: Calculate the "Fair Share" for the requested meal (e.g., Lunch = 35% of Daily Goal).
2. **Consumption Analysis**: Compare "Fair Share" with "Already Consumed".
3. **Adjustment**:
   - If a user over-consumed a macro early (e.g., 90% of Carbs at Breakfast), the "Fair Share" for Lunch is overridden.
   - The Copilot will suggest a meal that minimizes the over-consumed macro to keep the daily total $\le 90\%$ of the goal.
   - Protein is prioritized to ensure the user hits $\ge 100\%$ of their daily requirement.

## 3. Heuristics for Meal Suggestions
- **Carb-Heavy Start $\rightarrow$ Lean Mid-day**: If breakfast was high-carb, lunch is shifted to lean proteins and leafy greens.
- **Low-Energy Dip $\rightarrow$ Strategic Snack**: If consumed macros are very low by 4 PM, the snack is shifted to include healthy fats and moderate protein.
- **Safety Ceiling**: All suggestions are capped at 90% of the daily Carb/Fat limit to provide a safety buffer against estimation errors.
