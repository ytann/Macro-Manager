# PMOS Nutrition Knowledge Index
## For Gemma4:e2b Reasoning Engine

**Purpose**: Dense, trigger-based routing table for small LLM food recommendations + macro adjustments in PMOS/PCOD context.

**Context Window Optimization**: Each file 500-1000 tokens. Gemma loads specific file based on trigger.

---

## Quick Trigger Phrases → File Router

### Pathophysiology & Root Mechanisms
- **Trigger**: "Why is insulin high despite weight loss?" / "What's driving hyperandrogenism?" / "What's the connection between insulin and hormones?"
  - → Load: **01_IR_Pathophysiology.md**
  - **Contains**: IRS-1 serine phosphorylation block, tissue-specific IR profiles, selective ovarian paradox, macro intervention leverage

- **Trigger**: "How does PMOS develop?" / "What's the cascade?" / "Explain the vicious cycle"
  - → Load: **01_IR_Pathophysiology.md** + **04_Inflammation_Fiber_Lipids.md**
  - **Contains**: Root mechanism + DOGMA dysbiosis loop

---

### Macronutrient & Meal Recommendations (Primary Use Case)
- **Trigger**: "What should I eat?" / "My breakfast was high-carb, what about lunch?" / "How do I balance my macros?" / "I've used 60% carbs already"
  - → Load: **02_Macronutrient_Strategy.md**
  - **Contains**: 40/35/25 split rationale, protein/fat/fiber buffering mechanics, VPF sequencing, daily distribution strategy, recommendation algorithm

- **Trigger**: "What's the best time to eat?" / "Should I eat breakfast?" / "Is late-night eating bad?" / "When should I exercise?"
  - → Load: **03_Chrononutrition.md**
  - **Contains**: Diurnal glucose tolerance variation, melatonin-MTNR1B genotype effects, breakfast priming, TRE windows, LEO carryover, exercise timing

- **Trigger**: "Why are my macros strict?" / "Can I eat carbs at night?" / "My blood sugar is high"
  - → Load: **03_Chrononutrition.md** (timing rules)
  - **Consider**: Front-load carbs (breakfast/lunch priority), back-load protein/fat (dinner priority)

---

### Inflammation, Dysbiosis, Fiber
- **Trigger**: "I feel bloated" / "Digestive issues?" / "Should I take probiotics?" / "What about omega-3s?"
  - → Load: **04_Inflammation_Fiber_Lipids.md**
  - **Contains**: Dysbiosis → inflammation loop, fiber thresholds (25-36 g/day), soluble vs insoluble, omega-3 vs MUFA clinical evidence

- **Trigger**: "My LDL is high" / "What should I eat for cholesterol?" / "Anti-inflammatory diet?"
  - → Load: **04_Inflammation_Fiber_Lipids.md**
  - **Action**: MUFA-dominant (olive oil, avocado, nuts) > Omega-3 supplementation (unless >40yo)

- **Trigger**: "How much fiber?" / "What foods have fiber?" / "Will fiber help my hormones?"
  - → Load: **04_Inflammation_Fiber_Lipids.md**
  - **Target**: 28-36 g/day (optimal). Soluble + insoluble mix. Predicts ovulation restoration independent of weight loss.

---

## File Descriptions & Use Context

### 01_IR_Pathophysiology.md (~650 tokens)
**Audience**: Gemma's background reasoning layer.

**Contains**:
- IRS-1 Ser307/312 phosphorylation block mechanism
- Tissue-specific profiles: muscle (glucose disposal failure), liver (SHBG collapse), adipose (lipotoxicity)
- Selective ovarian IR paradox (why theca cells hyper-respond despite systemic IR)
- Compensatory HI loop
- Macro intervention strategy (protein/fat buffering, sequencing)

**Use**: When gemma needs to explain "why" behind recommendations. Internal reasoning support.

**Example Gemma Query**:
```
User: "I'm confused. The dietitian said high protein is good, but won't that spike insulin?"

Gemma (internally loads 02_Macronutrient_Strategy.md but reason using 01):
"You're right that protein ↑ insulin AUC. BUT in PMOS, the mechanism is different.
Your ovarian cells are insulin-SENSITIVE despite systemic resistance. The problem isn't
protein spiking insulin — it's NAKED CARBS causing chaotic, extreme insulin peaks that
overstimulate your ovaries. Protein buffering flattens the curve. Combined with timing
(breakfast > dinner), you're actually reducing total ovarian stimulus across the day."
```

---

### 02_Macronutrient_Strategy.md (~900 tokens)
**Audience**: Primary recommendation engine.

**Contains**:
- 40/35/25 clinical evidence (Wycherley, meta-analyses)
- Protein paradox explanation + source specificity (whey > casein timing)
- Fat buffering mechanisms + MUFA special role
- Fiber impact on insulin dynamics + clinical thresholds
- VPF sequencing trial data (40.9% glucose iAUC reduction, 31.7% insulin iAUC reduction)
- Bdiet vs Ddiet trial (high breakfast advantage)
- **Gemma Recommendation Algorithm** (e.g., "60% carbs at breakfast" → lunch/dinner allocation)

**Use**: Primary file for "what should I eat" queries. Drives daily meal recommendations.

**Example Gemma Query**:
```
User: "I had 120g carbs at breakfast out of 200g daily. What about lunch/dinner?"

Gemma (loads 02, runs algorithm):
1. Morning IR lowest (cortisol peak, GLP-1 max) → breakfast carbs well-tolerated ✓
2. Remaining CHO: 80g for lunch + dinner
3. Lunch = 60% of remaining (48g CHO) — still higher IR window than dinner but better than breakfast
   → Whey protein (fast, GLP-1-pre-priming) + olive oil + whole grain
   → 35C / 40P / 25F lunch macros
4. Dinner = 40% of remaining (32g CHO) — highest IR window (melatonin↑, cortisol↓)
   → Slow protein (casein/salmon) + avocado + broccoli + minimal rice
   → 25C / 45P / 30F dinner macros

Specific meal: [Grilled chicken + quinoa + olive oil + salad] for lunch
             [Salmon + roasted broccoli + avocado] for dinner
```

---

### 03_Chrononutrition.md (~950 tokens)
**Audience**: Timing + sequence recommendations.

**Contains**:
- Diurnal glucose tolerance rhythm (morning HIGH, evening LOW)
- Cortisol + melatonin physiology
- MTNR1B genotype interaction (late meal risk)
- Second-meal effect (breakfast priming)
- TRE meta-analysis (eTRE wins for HOMA-IR)
- LEO carryover (evening CHO → next-day FBG, r=0.878)
- Evening PA strategy (↓ IR 25%)
- Sleep-low method

**Use**: Time-based optimization. "When" layer on top of "what" (02_Macronutrient_Strategy).

**Example Gemma Query**:
```
User: "Should I have my largest meal at breakfast or dinner?"

Gemma (loads 03):
"Breakfast. The Jakubowicz RCT showed high-breakfast (Bdiet) beats high-dinner (Ddiet)
by: ↓ 20% daily glucose AUC, ↓ 25% post-lunch glucose (priming effect), ↓ 33.6% triglycerides.

Why: Cortisol peaks at 6-8 AM (max insulin sensitivity). Breakfast carbs → trigger GLP-1
→ primes β-cells → subsequent meals (lunch) tolerated better ('second-meal effect').

Evening: Melatonin ↑ suppresses insulin secretion (MT2 cAMP block). High-dinner = metabolic disaster.
Your next-day fasting glucose DEPENDS on last-night's glycemia (r=0.878 correlation)."
```

---

### 04_Inflammation_Fiber_Lipids.md (~850 tokens)
**Audience**: Lifestyle + supplement reasoning.

**Contains**:
- DOGMA (Dysbiosis of Gut Microbiota) loop: diet → dysbiosis → SCFA loss → barrier failure → endotoxemia → inflammation → IR amplification
- Dysbiosis fingerprint (Ruminococcus↑, Faecalibacterium↓)
- Systemic inflammation biomarkers (hs-CRP, TNF-α, IL-6)
- Fiber thresholds (25 g/day pathological, 28-36 g/day optimal, 40 g/day aggressive)
- Soluble vs insoluble mechanisms
- Omega-3 clinical profile (anti-inflammatory BUT no IR benefit)
- MUFA clinical profile (acts as PPAR-γ ligand, **directly reduces insulin + androgens**)

**Use**: Holistic metabolic support. Addresses inflammation, barrier integrity, supplement strategy.

**Example Gemma Query**:
```
User: "Should I take omega-3 supplements?"

Gemma (loads 04):
"Depends on age + inflammation status.

IF you're <40yo + normal hs-CRP:
→ Skip omega-3. Focus on dietary fiber (28-36g/day) instead. SCFA production repairs
  gut barrier, blocks LPS endotoxemia at source. More cost-effective.

IF you're >40yo + high hs-CRP + elevated cholesterol:
→ Fish oil 1.5-2g/day (EPA+DHA). Meta-analysis shows ↓ CRP + ↓ triglycerides (real benefit).

BUT in ALL ages:
→ Prioritize MUFAs (olive oil, avocado, nuts). They're natural PPAR-γ agonists.
  Clinical trial: MUFA diets ↓ fasting insulin, ↑ SHBG (which lowers free androgens).
  This is tier-1 intervention. Omega-3 is complementary only."
```

---

## Integration Strategy: Multi-File Reasoning

**Scenario**: User asks "I had high carbs at breakfast. My blood sugar is spiked. What should I eat now?"

**Gemma Multi-File Reasoning**:

1. **Load 02** (Macronutrient_Strategy): Understand 40/35/25 split, identify remaining CHO budget, recommend protein-heavy lunch
2. **Load 03** (Chrononutrition): Check current time → if 12 PM, insulin sensitivity still reasonable; if 6 PM, switch to evening protocol
3. **Load 04** (Inflammation_Fiber_Lipids): Ensure recommendation includes MUFA (olive oil) + fiber (if applicable) to manage inflammation
4. **Reference 01** (IR_Pathophysiology): Internal reasoning — "This user's theca cells are hyper-sensitive to insulin. I need to flatten the curve to reduce ovarian androgen stimulation."

**Final Output**:
```
"Since it's lunch (noon), your insulin sensitivity is still high. Protein buffering will help.

Recommendation:
→ Grilled chicken thigh (35g protein, MUFA-rich) + olive oil dressing + quinoa (48g CHO) + salad
→ Macro split: 35C / 40P / 25F (modified from daily 40/35/25 to exploit lunch window)
→ Timing: Eat salad + protein first (VPF sequencing), then carbs

Why: Protein/fat/fiber preload → GLP-1 pre-priming → delays CHO entry into duodenum
→ flattens both glucose AND insulin curves (↓ 40.9% glucose AUC, ↓ 31.7% insulin AUC vs mixed meal)
→ reduces ovarian theca cell stimulation for rest of day."
```

---

## File Loading Priority (Gemma Heuristics)

**For each user query, priority order**:

1. **Exact word match** (e.g., "breakfast" → prioritize 03_Chrononutrition)
2. **Intent detection** (e.g., "What should I eat?" → prioritize 02_Macronutrient_Strategy)
3. **Secondary context** (e.g., if macro + timing both mentioned, load 02 + 03 in parallel)
4. **Background reasoning** (e.g., if explanation needed, pull from 01_IR_Pathophysiology + 04_Inflammation)

---

## Update Strategy (Vector DB Future)

**Current**: Static markdown files. Gemma loads full file each query.

**Future**: Embed each file into vector DB. Chunk-level retrieval based on semantic similarity.

**Recommended chunking** (when vectorizing):
- Chunk size: ~300-400 tokens (sub-section level)
- Preserve table structure + code blocks as units
- Tag: `{file_id, chunk_idx, trigger_phrases[]}`

**Example chunk tags** (for 02_Macronutrient_Strategy.md):
```
chunk_1: "Optimal PMOS Macro Split"
  triggers: ["what macros", "40/35/25", "macro split", "protein/fat/carb ratio"]
  
chunk_7: "Gemma Recommendation Algorithm"
  triggers: ["I had X% carbs", "what should I eat", "meal recommendations", "remaining budget"]
  
chunk_11: "VPF Sequencing"
  triggers: ["blood sugar spike", "insulin spike", "food order", "what to eat first"]
```

**Retrieval**: On query, embed → find top-3 semantic chunks → synthesize across files as needed.

---

## Quick Reference: File Statistics

| File | Tokens | Topics | Trigger Count | Use Case |
|---|---|---|---|---|
| 01_IR_Pathophysiology.md | ~650 | IRS-1 block, tissue IR, ovarian paradox, macro leverage | 2 primary | Background reasoning |
| 02_Macronutrient_Strategy.md | ~900 | 40/35/25, protein/fat/fiber mechanics, VPF, Bdiet algorithm | 8+ primary | **PRIMARY: Meal recs** |
| 03_Chrononutrition.md | ~950 | Diurnal rhythm, melatonin, MTNR1B, breakfast priming, TRE, LEO | 6+ primary | Timing + sequencing |
| 04_Inflammation_Fiber_Lipids.md | ~850 | DOGMA loop, dysbiosis, fiber thresholds, omega-3 vs MUFA | 5+ primary | Holistic support |
| **Total** | **~3,350** | — | — | — |

---

## Sample Gemma Prompts (For Testing)

**Test 1**: "I had 150g carbs at breakfast (75% of my 200g daily allowance). What should I eat for lunch?"
- Expected load: 02_Macronutrient_Strategy.md (algorithm), 03_Chrononutrition.md (check timing), reference 01
- Expected output: Protein-heavy lunch, specific macro split, VPF sequencing instruction

**Test 2**: "Why should I avoid late dinners?"
- Expected load: 03_Chrononutrition.md (primary), 01_IR_Pathophysiology.md (reasoning)
- Expected output: Melatonin MT2 explanation, LEO glycemic carryover, evening IR mechanics

**Test 3**: "Should I take fish oil for inflammation?"
- Expected load: 04_Inflammation_Fiber_Lipids.md (primary), 03_Chrononutrition.md (if age context given)
- Expected output: Age-dependent recommendation, fiber-first strategy, MUFA prioritization

**Test 4**: "What's causing my high testosterone?"
- Expected load: 01_IR_Pathophysiology.md (primary), 02_Macronutrient_Strategy.md (intervention), 04 (DOGMA contribution)
- Expected output: SHBG collapse mechanism, IRS-1 block → HI → ovarian stimulation, macro buffer strategy

---

## Validation Checklist (Before Handoff to Gemma)

- [ ] All 4 files created and saved in `wiki/pmos_nutrition/` directory
- [ ] Each file 500-1000 tokens (confirm via word count)
- [ ] Trigger phrases in index match actual content in files
- [ ] No contradictions between files
- [ ] Clinical data (trial names, effect sizes, p-values) match reference documents
- [ ] Gemma recommendation algorithm in 02 is actionable (specific macro splits, sequencing order, timing rules)
- [ ] Pathophysiology (01) supports macro strategy (02)
- [ ] Chrononutrition (03) integrates with macro + pathophysiology seamlessly
- [ ] DOGMA + fiber (04) coherent with IR/HI/HA cascade (01)
