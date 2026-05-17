import os
import json
import re
import yaml
from app.core.logger import logger
from app.core.llm import safe_acompletion
# Adjust the model string to whatever you currently use for litellm/ollama in the rest of the app
LLM_MODEL = "ollama/gemma4:e2b" 

class PlannerService:
    def __init__(self):
        self.knowledge_dir = "wiki/pmos_nutrition"
        self.file_map = {
            "01": "01_IR_Pathophysiology.md",
            "02": "02_Macronutrient_Strategy.md",
            "03": "03_Chrononutrition.md",
            "04": "04_Inflammation_Fiber_Lipids.md"
        }
        # Load the newly created planner prompts
        with open("prompts/prompts.yaml", "r", encoding="utf-8") as f:
            self.prompts = yaml.safe_load(f).get("planner", {})

    async def generate_suggestion(self, user_query: str, remaining_macros: dict, memory_context: str = "") -> str:
        # STEP 0: LOAD SOVEREIGN MEMORY
        # Priority: passed memory_context > file-based glossary
        personal_glossary = memory_context
        
        # If no memory was passed, try to load from file
        if not personal_glossary:
            memory_path = "app/data/personal_glossary.md"
            if os.path.exists(memory_path):
                with open(memory_path, "r", encoding="utf-8") as f:
                    personal_glossary = f.read()

        # STEP 1: THE HYBRID ROUTER
        # 1.1 Deterministic Guard (Hard Safety Wall)
        routing_path = self._get_deterministic_path(user_query)
        
        # 1.2 LLM Routing (for file selection and nuanced pathing)
        router_text = self.prompts["router"].format(user_query=user_query)
        
        try:
            router_response = await safe_acompletion(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are a precise routing engine. Return ONLY a JSON object with 'files' (array) and 'path' (string)."},
                    {"role": "user", "content": router_text}
                ],
                temperature=0.0
            )
            raw_router = router_response.choices[0].message.content
            
            match = re.search(r'\{.*?\}', raw_router, re.DOTALL)
            if match:
                try:
                    router_data = json.loads(match.group(0))
                    file_ids = router_data.get("files", ["02"])
                    # LLM path only overrides if it's "clinical" OR if the guard didn't force clinical
                    llm_path = router_data.get("path", "clinical")
                    if routing_path == "clinical" or llm_path == "clinical":
                        routing_path = "clinical"
                    else:
                        routing_path = "fast"
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error in router: {e}")
                    file_ids = ["02"]
                    routing_path = "clinical"
            else:
                file_ids = ["02"]
                routing_path = "clinical"
        except Exception as e:
            logger.error(f"Router failed: {e}")
            file_ids = ["02"]
            routing_path = "clinical"
        
        # Guardrail: Limit to max 3 files
        file_ids = file_ids[:3]

        # --- FAST PATH OPTIMIZATION ---
        if routing_path == "fast":
            return await self._handle_fast_path(user_query, personal_glossary)

        # STEP 2: LOAD KNOWLEDGE (The Hands)
        pmos_context = ""
        for fid in file_ids:
            filename = self.file_map.get(str(fid).zfill(2))
            if filename:
                filepath = os.path.join(self.knowledge_dir, filename)
                if os.path.exists(filepath):
                    with open(filepath, "r", encoding="utf-8") as f:
                        pmos_context += f"--- {filename} ---\n{f.read()}\n\n"

        # STEP 3: THE CLINICAL COPILOT (Heavy Call)
        copilot_text = self.prompts["meal_copilot"].format(
            user_query=user_query,
            remaining_macros=json.dumps(remaining_macros),
            pmos_context=pmos_context,
            personal_glossary=personal_glossary
        )

        try:
            copilot_response = await safe_acompletion(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are the MacroManager Clinical Copilot. You must adhere strictly to the provided medical boundaries and clinical knowledge. Do not provide medical diagnoses or prescriptions. When making dietary recommendations, always include a 'Clinical Basis' section citing the provided context (e.g., 'Based on the VPF sequencing research in 02_Macronutrient_Strategy.md...')."},
                    {"role": "user", "content": copilot_text}
                ],
                temperature=0.2
            )
            return copilot_response.choices[0].message.content
        except Exception as e:
            return f"🚨 Copilot Error: Could not generate a meal plan. ({e})"

    def _get_deterministic_path(self, query: str) -> str:
        """Hard-coded safety wall to prevent clinical leaks into fast-path."""
        query_lower = query.lower()
        
        # 1. Fast-Path Guard: Force 'fast' for trivialities to reduce over-engineering
        fast_keywords = [
            "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
            "who are you", "what is your name", "how are you", "bye", "goodbye",
            "thanks", "thank you", "joke", "happy", "hear me"
        ]
        if any(word == query_lower or word in query_lower.split() for word in fast_keywords):
            # Only force fast if it's NOT also clinical
            # (e.g., "Hello, why is my insulin high?" should be clinical)
            clinical_check = [
                "pmos", "pcod", "insulin", "hormone", "ovary", "androgen", 
                "eat", "food", "meal", "rice", "sugar", "carb", "protein", "fat", 
                "macro", "split", "fiber", "pain", "abdominal", "symptom", 
                "diagnosis", "diagnose", "treatment", "weight", "glucose"
            ]
            if not any(word in query_lower for word in clinical_check):
                return "fast"

        # 2. Clinical-Path Guard: Force 'clinical' for safety-critical terms
        clinical_keywords = [
            "pmos", "pcod", "insulin", "hormone", "ovary", "androgen", 
            "eat", "food", "meal", "rice", "sugar", "carb", "protein", "fat", 
            "macro", "split", "fiber", "pain", "abdominal", "symptom", 
            "diagnosis", "diagnose", "treatment", "weight", "glucose", 
            "why", "how does", "recommend", "acne", "fatigue", "fatigued", "saturated"
        ]
        if any(word in query_lower for word in clinical_keywords):
            return "clinical"
            
        return "clinical" # Default to safest path

    async def _handle_fast_path(self, query: str, memory: str) -> str:
        """Handles trivial queries using a lightweight LLM call without loading the clinical wiki."""
        try:
            resp = await safe_acompletion(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are MacroManager, a helpful assistant. This is a fast-path response for a non-clinical query. Be brief, warm, and friendly. Do not provide medical advice. If the user asks for meal planning or clinical why, politely tell them you are switching to the Clinical Copilot mode now."},
                    {"role": "user", "content": f"User Memory: {memory}\n\nUser Query: {query}"}
                ],
                temperature=0.3
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"🚨 Fast-Path Error: {e}"
