# 🧪 Experimental Sprint 7: High-Precision Volumetric Vision Extraction

## 1. Overview
This sprint aims to solve the "wild" weight estimations of the current vision pipeline by replacing direct weight guessing with a physical calculation: **Geometric Volume $\times$ Food Density**. 

By anchoring estimations to the user's specific utensils (stored in Sovereign Memory) and enforcing a "sum-to-100%" volume constraint, we move from AI "guessing" to AI "calculating."

---

## 2. Technical Specification

### 2.1. The Volumetric Pipeline
1.  **Identity**: Gemma identifies food items + associated container.
2.  **Context**: System retrieves container dimensions from **Sovereign Memory**.
3.  **CoT Volume Evaluation**: Gemma estimates the **Fill Percentage** of each item relative to the container.
4.  **Constraint**: Total Volume $\sum(\text{Fill}\%) \le 100\%$.
5.  **Physics Layer**: Final Mass is calculated in Python:
    $$\text{Mass (g)} = (\text{Total Utensil Volume} \times \text{Fill}\%) \times \text{Density}(\text{g/cm}^3)$$

### 2.2. Components to Implement
- **Density Knowledge Base**: `app/core/densities.json` containing $\text{g/cm}^3$ for common PMOS foods.
- **Sovereign Memory Integration**: Logic to fetch utensil volumes (e.g., "Dinner Bowl: 500ml").
- **Volumetric Prompt**: A new multimodal prompt enforcing the Chain-of-Thought volume evaluation.
- **Calculation Engine**: A Python helper in `ExtractionService` to perform the final multiplication.

---

## 3. Execution Plan

### Phase 1: Knowledge Base & Foundation
- [ ] **Task 1.1**: Create `app/core/densities.json`.
    - Populate with average densities for: Grains, Legumes, Proteins, Leafy Greens, and Fats.
- [ ] **Task 1.2**: Define a "Standard Utensil" fallback set (e.g., Standard Bowl = 500ml, Standard Plate = 800ml) for users who haven't provided memory data.

### Phase 2: Prompt Engineering
- [ ] **Task 2.1**: Update `prompts/prompts.yaml` (`extraction.vision_estimate`).
    - Remove requests for "weight/grams."
    - Add requirement for: `Utensil Identification` $\rightarrow$ `Fill Percentage per Item` $\rightarrow$ `Volume Check (Sum $\le 100\%$)`.
- [ ] **Task 2.2**: Implement a "Chain of Volume" system prompt to force the model to reason about space before assigning percentages.

### Phase 3: Backend Logic Implementation
- [ ] **Task 3.1**: Update `app/services/extraction.py` $\rightarrow$ `extract_from_image()`.
    - Logic to parse the "Fill Percentage" from Gemma's output.
    - Logic to fetch utensil volume from `Sovereign Memory` $\rightarrow$ fallback to standard.
- [ ] **Task 3.2**: Implement the `calculate_mass_from_volume` helper.
    - $\text{Volume (ml)} \times \text{Density (g/ml)}$.
- [ ] **Task 3.3**: Integrate Tavily search to refine "Density Category" (e.g., "is this a dense or airy version of this food?").

### Phase 4: Verification & Testing
- [ ] **Task 4.1**: Unit tests for the Volume $\rightarrow$ Mass calculation.
- [ ] **Task 4.2**: "Golden Set" testing: Upload 10 photos of known volumes and compare the new volumetric output vs. previous "wild" output.
- [ ] **Task 4.3**: Edge case testing: Over-filled containers ($>100\%$) and unknown food densities.

---

## 4. Success Metrics
- **Accuracy**: $\pm 15\%$ variance compared to actual weighed food.
- **Plausibility**: Zero instances of physically impossible weights (e.g., 2kg of salad in a small bowl).
- **Consistency**: Identical images result in identical volumetric calculations.

## 5. Frontend Impact
- **None**: This is a pure backend upgrade. The `POST /vision-log` endpoint continues to return the same schema, but the `grams` value is now calculated via physics rather than guessed.
