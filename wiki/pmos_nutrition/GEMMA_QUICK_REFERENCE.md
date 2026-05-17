# Gemma Quick-Reference: PMOS Nutrition Decision Tree

**For ultra-fast query routing + reasoning without full file load.**

---

## Query Type → File + Action

### "What should I eat?" (MOST COMMON)
**Load**: 02_Macronutrient_Strategy.md
**Algorithm**:
1. Parse remaining CHO budget
2. Check current time (AM/PM)
3. If AM/midday: 35-40C% (high protein + fat)
4. If evening: 25C% (high protein + fat)
5. **ALWAYS**: VPF sequencing (Vegetables-Protein-Fat-Carbs order)
6. **Macro targets**: 35C/40P/25F (lunch), 25C/45P/30F (dinner)

**Output Example**: "Chicken thigh + olive oil + quinoa + salad → [specific macro % + sequencing instruction]"

---

### "My [macro/nutrient] is high/low, what should I do?" (SECOND MOST COMMON)
**Load**: 02 (if macro), 03 (if timing), 04 (if inflammation/fiber)

| Scenario | Load | Action |
|---|---|---|
| "60% carbs at breakfast" | 02 → Algorithm | Lunch 35C/40P/25F, Dinner 25C/45P/30F |
| "Blood sugar spiked" | 02 → VPF | Eat protein/fat FIRST, carbs last |
| "Insulin high despite diet" | 01 + 02 | Explain IRS-1 block + buffering strategy |
| "Testosterone still high" | 01 + 04 | SHBG collapse (IRS-1 block) + fiber/MUFA fixes |
| "Evening blood sugar bad" | 03 | Melatonin MT2 risk + lower dinner carbs |
| "Cholesterol high" | 04 | +5-10g soluble fiber + replace saturated with MUFA |

---

### "When should I eat?"
**Load**: 03_Chrononutrition.md

**Core Rules**:
- **Breakfast**: FRONT-LOAD carbs (50-60% daily CHO) → cortisol peak + max GLP-1
- **Lunch**: Moderate CHO (still high IR sensitivity) → 40-50% of remaining budget
- **Dinner**: MINIMIZE carbs (<30% daily CHO) → melatonin IR + cortisol nadir
- **Activity**: Evening MVPA ↓ IR 25% → recommend post-dinner walk

**LEO Rule**: Last eating occasion carbs directly predict next-day fasting glucose (r=0.878) → minimize evening carbs = better next-day baseline.

---

### "Should I take [supplement/have concerns about food]?"
**Load**: 04_Inflammation_Fiber_Lipids.md

| Question | Answer |
|---|---|
| Omega-3 supplements? | **Age-dependent**: <40yo → skip (focus fiber 28-36g/day). >40yo + high CRP/cholesterol → yes (1.5-2g fish oil) |
| Probiotics? | Static files don't deeply cover. General: helps dysbiosis but fiber priority |
| Fiber goal? | **28-36 g/day** optimal (soluble + insoluble mix). <25g = pathological failure |
| Saturated fat? | Replace with MUFA (olive oil, avocado, nuts) — they're natural PPAR-γ agonists |

---

## Multi-File Reasoning Examples

### Scenario 1: User has 40% carbs remaining
**Gemma's brain**:
1. Load 02: Remaining 40% = split 60% lunch, 40% dinner
2. Load 03: Check time. If 6 PM, move more to lunch, less to dinner
3. Load 01: Reason "why protein buffering helps" (theca cell paradox)
4. Load 04: Ensure MUFA included (PPAR-γ agonism)

**Output**: "Lunch: moderate CHO + high protein + MUFA. Dinner: low CHO + very high protein + fat."

---

### Scenario 2: User asks "Why is my testosterone high?"
**Gemma's brain**:
1. Load 01: SHBG collapse (HNF-4α suppressed via hyperinsulinemia + DNL + inflammatory cytokines)
2. Load 02: Recommend protein/fat buffering → lower insulin AUC → reduce SHBG suppression
3. Load 04: Dysbiosis (DOGMA) exacerbates via estrobolome dysfunction + Bacteroides dysregulation
4. Load 03: Evening carbs worsen HI → recommend morning-heavy + evening-light

**Output**: "High testosterone = low SHBG. Caused by hyperinsulinemia (insulin IRS-1 block → HI). Fix: protein buffers glucose, fiber repairs dysbiosis (→ less LPS → less inflammation → better insulin signaling)."

---

## Decision Tree: Yes/No Branches

```
User Query
    ↓
┌─ "What eat?" ──→ Load 02 → Macro Algorithm → VPF Sequencing ──→ [MEAL]
├─ "When eat?" ──→ Load 03 → Time windows (AM/PM) ──→ [TIMING]
├─ "Why high/low [X]?" ──→ Load appropriate file:
│   ├─ Macro issue → 02 + 03
│   ├─ Hormone issue → 01 + 02 + 04
│   ├─ Inflammation → 04
│   └─ Dysbiosis → 04
├─ "Supplement?" ──→ Load 04 → Age/biomarker check ──→ [RECOMMENDATION]
└─ Confused/Reasoning needed → Load 01 → Explain pathophysiology ──→ [INSIGHT]
```

---

## Trigger Phrase Shortcuts (Gemma's Mental Hotkeys)

| Phrase | File | Fast Output |
|---|---|---|
| "60% carbs" | 02 | Lunch 35C/40P/25F, Dinner 25C/45P/30F |
| "breakfast" | 03 | Front-load CHO, cortisol peak exploited |
| "dinner" | 03 | Low CHO, high protein/fat, melatonin risk |
| "spiked" | 02 | VPF sequencing (eat salad/protein first) |
| "fiber" | 04 | 28-36 g/day target (soluble + insoluble) |
| "omega-3" | 04 | Age-dependent (>40yo only if dyslipidemia) |
| "testosterone" | 01 + 04 | SHBG collapse (IRS-1) + dysbiosis |
| "cholesterol" | 04 | MUFA tier-1, soluble fiber, then omega-3 |
| "blood sugar" | 03 | Check time, melatonin IR risk if evening |
| "insulin high" | 01 | IRS-1 serine phosphorylation (systemic IR) |

---

## Macro Splits By Meal & Time

| Meal | Time | Macro Split | Reason |
|---|---|---|---|
| **Breakfast** | 6-10 AM | 40-50C / 35P / 15F | Cortisol peak, GLP-1 max, high IR sensitivity |
| **Lunch** | 12-2 PM | 35C / 40P / 25F | Modified to exploit GLP-1 priming + protein buffering |
| **Dinner** | 6-8 PM | 25C / 45P / 30F | Low CHO (melatonin IR risk), high protein (nocturnal stability), fat (prevents absorption spikes) |
| **Snack** | If needed | 20C / 40P / 40F | Protein/fat heavy, minimal CHO |

---

## Red Flags → Immediate Action

| Flag | Likely Cause | Action |
|---|---|---|
| Fasting insulin >15 IU/mL | Severe IR | Load 01 (IRS-1 explanation) + Load 02 (protein buffering) |
| Evening blood sugar >120 mg/dL | Melatonin IR / Late carbs | Load 03 (LEO rule) — reduce dinner CHO |
| hs-CRP >3 mg/L | Inflammation / Dysbiosis | Load 04 (fiber target 28-36g, MUFA priority) |
| Testosterone >80 ng/dL | SHBG collapse | Load 01 (HNF-4α suppression) + Load 04 (dysbiosis fix) |
| Can't lose weight | Hyperinsulinemia loop | Load 01 (theca overstimulation) + Load 04 (DOGMA dysbiosis) |

---

## VPF Sequencing Reminder

**When recommending meals, ALWAYS specify order**:

```
❌ Wrong: "Eat chicken, rice, and salad"
✓ Correct: "Eat salad + chicken (protein) FIRST [wait 2-3 min], then rice (carbs)"

Effect: ↓ 40.9% glucose iAUC, ↓ 31.7% insulin iAUC vs mixed meal
Reason: Pre-priming of GLP-1 + delayed CHO entry → flat curve
```

---

## Gemma's 3-Tier Confidence Levels

### Tier 1: HIGH Confidence (Use without hesitation)
- Macro allocation algorithm (02)
- VPF sequencing (02)
- Fiber targets 28-36g (04)
- MUFA > Omega-3 (04)
- Front-load breakfast carbs (03)

### Tier 2: MEDIUM Confidence (Explain reasoning)
- MTNR1B genotype personalization (03)
- Supplement recommendations (04)
- Exact meal timing windows (03)
- Dysbiosis intervention order (04)

### Tier 3: LOW Confidence (Flag for human review)
- Ketogenic diet protocols (NOT COVERED)
- Drug-nutrient interactions (NOT COVERED)
- Exercise modality specificity (strength vs cardio) (NOT DETAILED)
- Behavioral adherence strategies (NOT COVERED)

---

## Quick Copy-Paste Recommendation Template

```
Based on your remaining CHO budget & current time:

**Lunch** (if 12-3 PM):
- Protein: [WHEY-BASED or fast protein] (35-40g)
- Carbs: [WHOLE GRAIN] (X g CHO)
- Fat: Olive oil or avocado (MUFA)
- Fiber: +8-10g soluble (oats, legumes if possible)
- Macro split: 35C / 40P / 25F
- **Sequencing**: Eat salad + protein FIRST, then carbs

**Dinner** (if 6-8 PM):
- Protein: [SLOW PROTEIN like salmon/casein] (40-45g)
- Carbs: [MINIMAL, COMPLEX] (X g CHO)
- Fat: Avocado or nuts (MUFA)
- Fiber: Broccoli/leafy greens
- Macro split: 25C / 45P / 30F
- **AVOID**: Refined carbs, wheat, sugar after 6 PM

Expected benefit: ↓ glucose spike → ↓ ovarian theca stimulation → ↓ testosterone over time
```

---

## When Unsure → Load Multiple Files

**Rule**: If user's question touches >1 domain, load files in this order:
1. 02 (Macronutrient) — primary
2. 03 (Chrononutrition) — timing context
3. 04 (Inflammation/Fiber) — holistic support
4. 01 (Pathophysiology) — reasoning only if explanation needed

---

## Final Gemma Mantra

**"Control insulin curve = control theca cell stimulation = reduce androgens. Protein/fat/fiber buffering + VPF sequencing + circadian timing = flatter curve."**

Every recommendation should trace back to this principle.
