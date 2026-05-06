import litellm
import json
import yaml
import asyncio
from typing import List, Optional, Dict, Any
from app.services.foodbank import FoodbankService
from app.schemas.food_schemas import FoodItem, FoodLog, Macros, SubMacros
from app.services.database import DatabaseManager
from app.core.config import Config

class ExtractionService:
    """
    Handles the Two-Pass Extraction Pipeline:
    Initial Extraction -> Verification Guardrail -> Deduplication -> Nutrition Calculation.
    """
    def __init__(self, foodbank_service: FoodbankService):
        self.foodbank = foodbank_service
        self.prompts = self._load_prompts()
        litellm.api_base = Config.LITELLM_API_BASE
        self.model = Config.LLM_MODEL

    def _load_prompts(self) -> Dict:
        with open(Config.PROMPTS_PATH, 'r') as f:
            return yaml.safe_load(f)

    async def _verify_extracted_items(self, text: str, items: List[dict]) -> List[dict]:
        found_details = [f"{i.get('name')} ({i.get('grams')}g)" for i in items]
        prompt = self.prompts['extraction']['verification'].format(text=text, found_details=found_details)
        try:
            resp = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                api_base=Config.LITELLM_API_BASE,
                temperature=0.0
            )
            data = json.loads(resp.choices[0].message.content)
            return data.get('missing', [])
        except Exception as e:
            print(f"Verification guardrail failed: {e}")
            return []

    def _deduplicate_items(self, items: List[dict]) -> List[dict]:
        junk_terms = {'plate', 'bowl', 'glass', 'piece', 'serving', 'portion', 'cup'}
        unique_items = []
        seen_names = set()
        for item in items:
            name = item.get('name', '').lower().strip()
            if not name or any(term == name for term in junk_terms):
                continue
            is_duplicate = any(name in seen or seen in name for seen in seen_names)
            if not is_duplicate:
                unique_items.append(item)
                seen_names.add(name)
        return unique_items

    async def _process_base_ingredient(self, name: str, grams: float, state: Dict[str, float], parsed_items: List[FoodItem]):
        food_data = await self.foodbank.get_nutrition_data(name)
        
        if not food_data:
            return

        # --- CALORIC GUARDRAIL ---
        raw_p = float(food_data.get('protein') or 0)
        raw_c = float(food_data.get('carbs') or 0)
        raw_f = float(food_data.get('fat') or 0)
        raw_cal = float(food_data.get('calories') or 0)
        
        expected_cal = (raw_p * 4) + (raw_c * 4) + (raw_f * 9)
        if raw_cal > 0 and abs(raw_cal - expected_cal) / raw_cal > 0.2:
            raw_cal = expected_cal
        
        p = (raw_p / 100) * grams
        c = (raw_c / 100) * grams
        f = (raw_f / 100) * grams
        cal = (raw_cal / 100) * grams
        sub = SubMacros(fiber=(float(food_data.get('fiber') or 0) / 100) * grams if food_data.get('fiber') is not None else None)
        
        state['p'] += p
        state['c'] += c
        state['f'] += f
        state['cal'] += cal
        parsed_items.append(FoodItem(name=name, grams=grams, cals=cal, macros=Macros(protein=p, carbs=c, fat=f), sub_macros=sub))

    async def parse(self, text: str, meal_id: str = "unknown") -> FoodLog:
        prompt = self.prompts['extraction']['main'].format(text=text)
        resp = await litellm.acompletion(
            model=self.model, 
            messages=[{"role": "user", "content": prompt}], 
            response_format={"type": "json_object"}, 
            api_base=Config.LITELLM_API_BASE,
            temperature=0.0
        )
        data = json.loads(resp.choices[0].message.content)
        
        items_list = []
        if isinstance(data, dict):
            for k in ['items', 'ingredients', 'data', 'response']:
                if k in data and isinstance(data[k], list):
                    items_list = data[k]
                    break
            if not items_list:
                for v in data.values():
                    if isinstance(v, list):
                        items_list = v
                        break
        elif isinstance(data, list):
            items_list = data

        missing = await self._verify_extracted_items(text, items_list)
        items_list.extend(missing)
        items_list = self._deduplicate_items(items_list)

        parsed_items = []
        state = {'p': 0.0, 'c': 0.0, 'f': 0.0, 'cal': 0.0}
        
        # Process ingredients in parallel
        tasks = []
        for item in items_list:
            name = item.get('name')
            grams = float(item.get('grams') or 0)
            tasks.append(self._process_base_ingredient(name, grams, state, parsed_items))
        
        await asyncio.gather(*tasks)

        if not parsed_items:
            raise ValueError("No valid food items extracted.")
        
        return FoodLog(
            meal_id=meal_id, items=parsed_items, 
            total_macros=Macros(protein=state['p'], carbs=state['c'], fat=state['f']),
            total_calories=state['cal'], confidence_score=1.0
        )
