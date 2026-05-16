import os
import json
import re
import yaml
from litellm import acompletion
# Adjust the model string to whatever you currently use for litellm/ollama in the rest of the app
LLM_MODEL = "ollama/gemma4:e2b" 

class PlannerService:
    def __init__(self):
        self.knowledge_dir = "wiki/pcos_nutrition"
        self.file_map = {
            "01": "01_IR_Pathophysiology.md",
            "02": "02_Macronutrient_Strategy.md",
            "03": "03_Chrononutrition.md",
            "04": "04_Inflammation_Fiber_Lipids.md"
        }
        # Load the newly created planner prompts
        with open("prompts/prompts.yaml", "r", encoding="utf-8") as f:
            self.prompts = yaml.safe_load(f).get("planner", {})

    async def generate_suggestion(self, user_query: str, remaining_macros: dict) -> str:
        # STEP 0: LOAD SOVEREIGN MEMORY
        personal_glossary = ""
        memory_path = "app/data/personal_glossary.md"
        if os.path.exists(memory_path):
            with open(memory_path, "r", encoding="utf-8") as f:
                personal_glossary = f.read()

        # STEP 1: THE ROUTER (Fast Call)
        router_text = self.prompts["router"].format(user_query=user_query)
        
        try:
            router_response = await acompletion(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are a precise routing engine. Return ONLY a JSON array of IDs."},
                    {"role": "user", "content": router_text}
                ],
                temperature=0.0
            )
            raw_router = router_response.choices[0].message.content
            
            # Safety Net: Extract array even if wrapped in markdown (e.g. ```json ["02"] ```)
            match = re.search(r'\[.*?\]', raw_router, re.DOTALL)
            if match:
                file_ids = json.loads(match.group(0))
            else:
                file_ids = ["02"] # Safe fallback to main meal strategy
        except Exception as e:
            print(f"Router failed: {e}")
            file_ids = ["02"] # Safe fallback
        
        # Guardrail: Limit to max 3 files so we don't blow out the context window
        file_ids = file_ids[:3]

        # STEP 2: LOAD KNOWLEDGE (The Hands)
        pcos_context = ""
        for fid in file_ids:
            # Ensure format is always "01", "02", etc.
            filename = self.file_map.get(str(fid).zfill(2))
            if filename:
                filepath = os.path.join(self.knowledge_dir, filename)
                if os.path.exists(filepath):
                    with open(filepath, "r", encoding="utf-8") as f:
                        pcos_context += f"--- {filename} ---\n{f.read()}\n\n"

        # STEP 3: THE CLINICAL COPILOT (Heavy Call)
        copilot_text = self.prompts["meal_copilot"].format(
            user_query=user_query,
            remaining_macros=json.dumps(remaining_macros),
            pcos_context=pcos_context,
            personal_glossary=personal_glossary
        )

        try:
            copilot_response = await acompletion(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are the MacroManager Clinical Copilot. You must adhere strictly to the provided medical boundaries and clinical knowledge. Do not provide medical diagnoses or prescriptions."},
                    {"role": "user", "content": copilot_text}
                ],
                temperature=0.2 # Slight creativity for meal planning
            )
            return copilot_response.choices[0].message.content
        except Exception as e:
            return f"🚨 Copilot Error: Could not generate a meal plan. ({e})"
