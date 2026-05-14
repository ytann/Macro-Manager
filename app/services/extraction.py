import litellm
import json
import yaml
import asyncio
import uuid
import os
from typing import List, Optional, Dict, Tuple
from app.services.foodbank import FoodbankService
from app.schemas.food_schemas import FoodItem, FoodLog, Macros, SubMacros
from app.services.database import DatabaseManager
from app.core.config import Config
from app.core.logger import logger

async def parse_food_log(text: str, meal_id: str = "unknown"):
    """Backward compatibility helper for tests."""
    db = DatabaseManager()
    from app.services.foodbank import FoodbankService
    fb = FoodbankService(db)
    service = ExtractionService(fb)
    return await service.parse(text, meal_id)

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
        self.foodbank_cache = {}

    def _load_prompts(self) -> Dict:
        with open(Config.PROMPTS_PATH, 'r') as f:
            return yaml.safe_load(f)

    def _get_user_memory(self) -> str:
        path = "app/data/personal_glossary.md"
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.read()
        return ""

    async def extract_from_image(self, base64_image: str, environment: str = "Home", hint: str = "") -> FoodLog:
        prompt = self.prompts['extraction']['vision_estimate'].format(
            environment=environment, 
            hint=hint, 
            user_memory=self._get_user_memory()
        )

        resp = await litellm.acompletion(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }],
            api_base=Config.LITELLM_API_BASE,
            temperature=0.0,
            response_format={"type": "json_object"}
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

        unique_items = self._deduplicate_items(items_list)
        meal_id = f"vision_{uuid.uuid4().hex[:8]}"
        return await self._resolve_and_build_log(unique_items, meal_id)

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
            logger.error(f"Verification guardrail failed: {e}")
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

    async def _get_nutrition_for_ingredient(self, name: str, grams: float) -> Optional[Tuple[Dict[str, float], FoodItem]]:
        """Thread-safe nutrition resolution. Returns (macro_delta, FoodItem) or None."""
        cache_key = name.lower()
        if cache_key in self.foodbank_cache:
            food_data = self.foodbank_cache[cache_key]
        else:
            food_data = await self.foodbank.get_nutrition_data(name)
            if food_data:
                self.foodbank_cache[cache_key] = food_data

        if not food_data:
            return None

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

        sub = SubMacros(
            fiber=(float(food_data.get('fiber') or 0) / 100) * grams if food_data.get('fiber') is not None else None,
            sugar=(float(food_data.get('sugar') or 0) / 100) * grams if food_data.get('sugar') is not None else None,
            saturated_fat=(float(food_data.get('saturated_fat') or 0) / 100) * grams if food_data.get('saturated_fat') is not None else None,
            unsaturated_fat=(float(food_data.get('unsaturated_fat') or 0) / 100) * grams if food_data.get('unsaturated_fat') is not None else None
        )

        delta = {'p': p, 'c': c, 'f': f, 'cal': cal}
        food_item = FoodItem(
            name=name, grams=grams, cals=cal,
            macros=Macros(protein=p, carbs=c, fat=f),
            sub_macros=sub,
            verified=bool(food_data.get('verified'))
        )
        return (delta, food_item)

    async def _expand_recipe(self, recipe: List[Dict], scale: float) -> Tuple[List[FoodItem], Dict[str, float]]:
        """Expand recipe ingredients in parallel. Returns (ingredient_items, totals)."""
        tasks = []
        for ingred in recipe:
            name = ingred.get('name')
            g = float(ingred.get('grams') or 0) * scale
            tasks.append(self._get_nutrition_for_ingredient(name, g))

        results = await asyncio.gather(*tasks)

        ingredients = []
        delta = {'p': 0.0, 'c': 0.0, 'f': 0.0, 'cal': 0.0}
        for result in results:
            if result is None:
                continue
            d, item = result
            for k in delta:
                delta[k] += d[k]
            ingredients.append(item)
        return ingredients, delta

    async def _resolve_and_build_log(self, items_list: List[dict], meal_id: str) -> FoodLog:
        parsed_items = []
        state = {'p': 0.0, 'c': 0.0, 'f': 0.0, 'cal': 0.0}

        base_tasks = []
        base_metadata = []

        for item in items_list:
            name = item.get('name')
            grams = float(item.get('grams') or 0)

            recipe = await self.foodbank.get_recipe(name)
            if recipe:
                total_w = sum(float(i.get('grams') or 0) for i in recipe)
                scale = grams / total_w if total_w > 0 else 1
                recipe_items, recipe_delta = await self._expand_recipe(recipe, scale)

                dish_cals = sum(it.cals for it in recipe_items)
                dish_summary = FoodItem(
                    name=f"{name} (Total)", grams=grams,
                    cals=dish_cals,
                    macros=Macros(
                        protein=sum(it.macros.protein for it in recipe_items),
                        carbs=sum(it.macros.carbs for it in recipe_items),
                        fat=sum(it.macros.fat for it in recipe_items)
                    )
                )
                parsed_items.append(dish_summary)
                parsed_items.extend(recipe_items)
                for k in state:
                    state[k] += recipe_delta[k]
            else:
                base_metadata.append((len(base_tasks), name, grams))
                base_tasks.append(self._get_nutrition_for_ingredient(name, grams))

        results = []
        if base_tasks:
            results = await asyncio.gather(*base_tasks)

        for result in results:
            if result is None:
                continue
            d, item = result
            for k in state:
                state[k] += d[k]
            parsed_items.append(item)

        if not parsed_items:
            raise ValueError("No valid food items extracted.")

        return FoodLog(
            meal_id=meal_id, items=parsed_items,
            total_macros=Macros(protein=state['p'], carbs=state['c'], fat=state['f']),
            total_calories=state['cal'], confidence_score=1.0
        )

    async def parse(self, text: str, meal_id: str = "unknown") -> FoodLog:
        self.foodbank_cache.clear()

        # Voice Correction Pass: Normalize phonetic errors before extraction
        correction_prompt = self.prompts['extraction']['voice_correction'].format(text=text)
        try:
            corr_resp = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": correction_prompt}],
                api_base=Config.LITELLM_API_BASE,
                temperature=0.0
            )
            text = corr_resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Voice correction failed, proceeding with raw text: {e}")

        prompt = self.prompts['extraction']['main'].format(
            text=text, 
            user_memory=self._get_user_memory()
        )
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

        return await self._resolve_and_build_log(items_list, meal_id)
