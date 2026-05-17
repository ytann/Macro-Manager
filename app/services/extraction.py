import litellm
import json
import yaml
import asyncio
import uuid
import os
from typing import List, Optional, Dict, Tuple
from app.services.foodbank import FoodbankService
from app.services.barcode_decoder import decode_barcode_async
from app.schemas.food_schemas import FoodItem, FoodLog, Macros, SubMacros
from app.services.database import DatabaseManager
from app.core.config import Config
from app.core.logger import logger
from app.core.llm import safe_acompletion

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

    def _get_utensil_volume(self, utensil_name: str) -> float:
        """Retrieves utensil volume in ml. Checks memory first, then fallbacks."""
        memory = self._get_user_memory().lower()
        # Simple regex-like search in memory for "utensil_name: 500ml" or "utensil_name is 500ml"
        if utensil_name and utensil_name.lower() in memory:
            import re
            pattern = rf"{re.escape(utensil_name.lower())}.*?(\d+)\s*ml"
            match = re.search(pattern, memory)
            if match:
                return float(match.group(1))
        
        # Fallback to config
        from app.core.config import ClinicalConstants
        return float(ClinicalConstants.STANDARD_UTENSILS.get(utensil_name.lower(), ClinicalConstants.STANDARD_UTENSILS["default"]))

    STACKED_ITEMS_BASE_WEIGHTS = {
        "roti": 50.0, "chapati": 50.0, "phulka": 50.0,
        "naan": 90.0, "puri": 40.0, "paratha": 80.0,
        "dosa": 150.0, "idli": 45.0, "slice": 50.0, "tortilla": 40.0
    }

    def _calculate_mass(self, item_name: str, fill_percentage: float, utensil_vol: float, unit_count: Optional[int] = None) -> float:
        """Calculates mass. Prioritizes unit_count for stacked items, else uses Vol * Density."""
        name_lower = item_name.lower()
        
        # 1. Unit-Based Estimation (Guardrail for stacked items)
        if unit_count is not None and unit_count > 0:
            for keyword, weight in self.STACKED_ITEMS_BASE_WEIGHTS.items():
                if keyword in name_lower:
                    return float(unit_count * weight)

        # 2. Volumetric Estimation
        try:
            with open("app/core/densities.json", 'r') as f:
                densities = json.load(f)
        except Exception:
            return (utensil_vol * (fill_percentage / 100.0)) * 0.8 # Ultimate fallback

        normalized_name = name_lower.replace(" ", "_")
        
        # Check specific densities (both normalized and original)
        density = densities["specific"].get(normalized_name) or densities["specific"].get(name_lower)
        
        # Fallback to category density
        if density is None:
            cat_map = {
                "rice": "grains_cooked", "quinoa": "grains_cooked", "pasta": "grains_cooked",
                "dal": "legumes_cooked", "lentil": "legumes_cooked", "bean": "legumes_cooked",
                "chicken": "lean_proteins", "fish": "lean_proteins", "tofu": "lean_proteins",
                "spinach": "leafy_greens", "kale": "leafy_greens",
                "broccoli": "cruciferous_vegetables", "cauliflower": "cruciferous_vegetables",
                "carrot": "dense_vegetables", "potato": "dense_vegetables",
                "oil": "fats_oils", "butter": "fats_oils", "ghee": "fats_oils",
                "apple": "fruits_dense", "banana": "fruits_dense",
                "cucumber": "fruits_watery", "watermelon": "fruits_watery",
                "yogurt": "dairy_thick", "cheese": "dairy_thick"
            }
            for kw, cat in cat_map.items():
                if kw in name_lower:
                    density = densities["categories"].get(cat)
                    break
        
        if density is None:
            density = densities["fallbacks"]["default_density"]
            
        return (utensil_vol * (fill_percentage / 100.0)) * density

    async def extract_from_image(self, base64_image: str, environment: str, hint: str = "", meal_type: str = "General") -> FoodLog:
        # Limit image size to ~10MB binary (approx 13.3MB base64)
        if len(base64_image) > 13_300_000:
            raise ValueError("Image too large. Please upload an image smaller than 10MB.")

        prompt = self.prompts['extraction']['vision_estimate'].format(
            environment=environment, 
            hint=hint, 
            user_memory=self._get_user_memory()
        )

        resp = await safe_acompletion(
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

        try:
            data = json.loads(resp.choices[0].message.content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in extract_from_image: {e}")
            data = {}

        # Volumetric processing
        utensil = data.get("utensil", "default")
        utensil_vol = self._get_utensil_volume(utensil)
        
        raw_items = data.get("items", [])
        if not isinstance(raw_items, list):
            raw_items = []

        # Parallel Pipeline: 
        # 1. Fetch/Update nutrition from Tavily (via Foodbank)
        # 2. Calculate volumetric mass
        
        async def process_item(item_data):
            name = item_data.get("name", "unknown item")
            
            # Fallback guardrail: Ensure environment context is passed to the search engine if the LLM forgot
            if environment.lower() in ["street food", "restaurant"] and environment.lower() not in name.lower():
                name = f"{environment.title()} {name}"
                
            fill_pct = float(item_data.get("fill_percentage", 0.0))
            unit_count = item_data.get("unit_count")
            if unit_count is not None:
                try:
                    unit_count = int(unit_count)
                except (ValueError, TypeError):
                    unit_count = None
            
            # Path A: Trigger nutrition update (Upsert into DB using Tavily search)
            # This ensures that when _resolve_and_build_log is called, the data is fresh
            await self.foodbank.find_source_of_truth(name, upsert=True)
            
            # Path B: Calculate mass (Unit-based or Volumetric)
            grams = self._calculate_mass(name, fill_pct, utensil_vol, unit_count)
            
            return {"name": name, "grams": grams}

        items_list = await asyncio.gather(*[process_item(item) for item in raw_items])

        unique_items = self._deduplicate_items(items_list)
        meal_id = f"vision_{uuid.uuid4().hex[:8]}"
        return await self._resolve_and_build_log(unique_items, meal_id)

    async def extract_from_label(self, base64_image: str, hint: str = "", meal_type: str = "General", quantity: Optional[float] = None) -> FoodLog:
        """Extracts nutrition data directly from a nutrition label image."""
        if len(base64_image) > 13_300_000:
            raise ValueError("Image too large. Please upload an image smaller than 10MB.")

        prompt = self.prompts['extraction']['label_extraction']
        
        # We append the hint if available
        if hint:
            prompt += f"\n\nUSER HINT: {hint}"

        resp = await safe_acompletion(
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

        try:
            data = json.loads(resp.choices[0].message.content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in extract_from_label: {e}")
            raise ValueError("Failed to read nutrition label.")

        if data.get("error"):
            raise ValueError(f"Label extraction failed: {data.get('message', 'Unknown error')}")

        product_name = data.get("product_name") or hint or "Unknown Packaged Food"
        reported_qty = float(data.get("reported_qty") or 100.0)
        protein = float(data.get("protein") or 0.0)
        carbs = float(data.get("carbs") or 0.0)
        fat = float(data.get("fat") or 0.0)
        calories = float(data.get("calories") or ((protein * 4) + (carbs * 4) + (fat * 9)))
        fiber = float(data.get("fiber") or 0.0)
        
        # 1. Normalize and Upsert to DB (verified=1)
        await self.foodbank.normalize_and_upsert(
            name=product_name,
            reported_qty=reported_qty,
            protein=protein,
            carbs=carbs,
            fat=fat,
            calories=calories,
            fiber=fiber,
            source="label_scan",
            verified=1
        )
        
        # 2. Add to log (assume they are logging 1 serving/reported_qty if not specified)
        # For a label scan, we log the reported quantity as the consumed amount, unless explicitly provided.
        consumed_qty = quantity if quantity is not None and quantity > 0 else reported_qty
        items_list = [{"name": product_name, "grams": consumed_qty}]
        
        meal_id = f"label_{uuid.uuid4().hex[:8]}"
        return await self._resolve_and_build_log(items_list, meal_id)

    async def extract_from_qr(self, base64_image: str, hint: str = "", meal_type: str = "General", quantity: Optional[float] = None) -> FoodLog:
        """Decodes QR/Barcode and fetches macros."""
        # 1. Decode Barcode
        barcode_result = await decode_barcode_async(base64_image)
        
        barcode_data = None
        if barcode_result:
            barcode_data = barcode_result['data']
        else:
            # Fallback: Use LLM to read the numbers off the barcode
            logger.info("pyzbar failed. Falling back to Vision LLM to read barcode numbers.")
            prompt = "Extract ONLY the numbers below the barcode in this image. Return a JSON object with 'barcode': 'number' or 'error' if none found. No markdown."
            try:
                resp = await safe_acompletion(
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
                barcode_data = data.get('barcode')
                if barcode_data:
                    # Clean up any spaces
                    barcode_data = barcode_data.replace(" ", "")
            except Exception as e:
                logger.error(f"Vision fallback for barcode failed: {e}")
                
        if not barcode_data:
            raise ValueError("No QR or Barcode detected in the image.")
            
        product_name = hint or f"Product {barcode_data}"
        
        # 2. Try OpenFoodFacts API first
        import httpx
        off_url = f"https://world.openfoodfacts.org/api/v0/product/{barcode_data}.json"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(off_url, timeout=5.0)
                if response.status_code == 200:
                    off_data = response.json()
                    if off_data.get('status') == 1:
                        product = off_data.get('product', {})
                        nutriments = product.get('nutriments', {})
                        
                        # Extract data from OFF
                        off_name = product.get('product_name', '')
                        if off_name:
                            product_name = off_name
                            
                        # OFF usually provides per 100g, but we can check
                        cal_100 = float(nutriments.get('energy-kcal_100g') or nutriments.get('energy-kcal_value') or 0.0)
                        p_100 = float(nutriments.get('proteins_100g') or nutriments.get('proteins_value') or 0.0)
                        c_100 = float(nutriments.get('carbohydrates_100g') or nutriments.get('carbohydrates_value') or 0.0)
                        f_100 = float(nutriments.get('fat_100g') or nutriments.get('fat_value') or 0.0)
                        fiber_100 = float(nutriments.get('fiber_100g') or nutriments.get('fiber_value') or 0.0)
                        
                        if p_100 > 0 or c_100 > 0 or f_100 > 0:
                            logger.info(f"Found {product_name} on OpenFoodFacts!")
                            await self.foodbank.upsert_food(
                                name=product_name,
                                calories=cal_100,
                                protein=p_100,
                                carbs=c_100,
                                fat=f_100,
                                fiber=fiber_100,
                                verified=1,
                                source="openfoodfacts"
                            )
                            
                            consumed_qty = quantity if quantity is not None and quantity > 0 else 100.0
                            items_list = [{"name": product_name, "grams": consumed_qty}]
                            meal_id = f"qr_{uuid.uuid4().hex[:8]}"
                            return await self._resolve_and_build_log(items_list, meal_id)
        except Exception as e:
            logger.warning(f"OpenFoodFacts lookup failed for {barcode_data}: {e}")
            
        # 3. Fallback to Tavily
        logger.info(f"Falling back to Tavily for barcode {barcode_data}")
        search_term = hint if hint else barcode_data
        
        # Trigger Tavily search and DB upsert
        truth = await self.foodbank.find_source_of_truth(search_term, upsert=True)
        
        if not truth or truth.get('error'):
            raise ValueError(f"Could not find nutrition data for barcode {barcode_data}. Try taking a photo of the Nutrition Label instead.")
            
        # 4. Add to log (default to 100g if we don't know the package size)
        consumed_qty = quantity if quantity is not None and quantity > 0 else 100.0
        items_list = [{"name": search_term, "grams": consumed_qty}]
        
        meal_id = f"qr_{uuid.uuid4().hex[:8]}"
        return await self._resolve_and_build_log(items_list, meal_id)

    async def _verify_extracted_items(self, text: str, items: List[dict]) -> List[dict]:
        found_details = [f"{i.get('name')} ({i.get('grams')}g)" for i in items]
        prompt = self.prompts['extraction']['verification'].format(text=text, found_details=found_details)
        try:
            resp = await safe_acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                api_base=Config.LITELLM_API_BASE,
                temperature=0.0
            )
            try:
                data = json.loads(resp.choices[0].message.content)
                return data.get('missing', [])
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in verification guardrail: {e}")
                return []
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
            logger.warning(f"No nutrition data found for {name}, including as 0-macro item.")
            food_data = {'protein': 0, 'carbs': 0, 'fat': 0, 'calories': 0, 'verified': 0}

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

        # 1. Fetch all recipes in parallel
        recipe_tasks = [self.foodbank.get_recipe(item.get('name')) for item in items_list]
        recipes_results = await asyncio.gather(*recipe_tasks)

        # 2. Prepare all resolution tasks (recipes and base items) in parallel
        resolution_tasks = []
        task_metadata = [] # Store (type, name, grams, recipe_data)

        for i, item in enumerate(items_list):
            name = item.get('name')
            grams = float(item.get('grams') or 0)
            recipe = recipes_results[i]

            if recipe:
                total_w = sum(float(ing.get('grams') or 0) for ing in recipe)
                scale = grams / total_w if total_w > 0 else 1
                # Task to expand recipe
                resolution_tasks.append(self._expand_recipe(recipe, scale))
                task_metadata.append(('recipe', name, grams, recipe))
            else:
                # Task to resolve base nutrition
                resolution_tasks.append(self._get_nutrition_for_ingredient(name, grams))
                task_metadata.append(('base', name, grams, None))

        # 3. Gather all nutrition resolutions concurrently
        results = await asyncio.gather(*resolution_tasks)

        # 4. Process results and build the log
        for idx, result in enumerate(results):
            mtype, name, grams, recipe_data = task_metadata[idx]

            if mtype == 'recipe':
                recipe_items, recipe_delta = result
                dish_cals = sum(it.cals for it in recipe_items)
                dish_summary = FoodItem(
                    name=f"{name} (Total)", grams=grams,
                    cals=dish_cals,
                    macros=Macros(
                        protein=sum(it.macros.protein for it in recipe_items),
                        carbs=sum(it.macros.carbs for it in recipe_items),
                        fat=sum(it.macros.fat for it in recipe_items)
                    ),
                    sub_macros=SubMacros(
                        fiber=sum((it.sub_macros.fiber or 0) for it in recipe_items if it.sub_macros),
                        sugar=sum((it.sub_macros.sugar or 0) for it in recipe_items if it.sub_macros),
                        saturated_fat=sum((it.sub_macros.saturated_fat or 0) for it in recipe_items if it.sub_macros),
                        unsaturated_fat=sum((it.sub_macros.unsaturated_fat or 0) for it in recipe_items if it.sub_macros),
                    )
                )
                parsed_items.append(dish_summary)
                parsed_items.extend(recipe_items)
                for k in state:
                    state[k] += recipe_delta[k]
            else:
                if result is None:
                    fallback_item = FoodItem(
                        name=name, grams=grams, cals=0.0,
                        macros=Macros(protein=0.0, carbs=0.0, fat=0.0),
                        verified=False
                    )
                    parsed_items.append(fallback_item)
                    logger.warning(f"Nutrition resolution failed for {name}, keeping item with 0 macros.")
                else:
                    d, item = result
                    for k in state:
                        state[k] += d[k]
                    parsed_items.append(item)

        if not parsed_items:
            return FoodLog(
                meal_id=meal_id, items=[],
                total_macros=Macros(protein=0.0, carbs=0.0, fat=0.0),
                total_sub_macros=SubMacros(),
                total_calories=0.0, confidence_score=0.0
            )

        return FoodLog(
            meal_id=meal_id, items=parsed_items,
            total_macros=Macros(protein=state['p'], carbs=state['c'], fat=state['f']),
            total_sub_macros=SubMacros(
                fiber=sum((it.sub_macros.fiber or 0) for it in parsed_items if it.sub_macros),
                sugar=sum((it.sub_macros.sugar or 0) for it in parsed_items if it.sub_macros),
                saturated_fat=sum((it.sub_macros.saturated_fat or 0) for it in parsed_items if it.sub_macros),
                unsaturated_fat=sum((it.sub_macros.unsaturated_fat or 0) for it in parsed_items if it.sub_macros),
            ),
            total_calories=state['cal'], confidence_score=1.0
        )

    async def extract_items(self, text: str, is_voice: bool = False, meal_type: str = "General") -> Tuple[List[dict], str]:
        """
        Phase 1 of Async Pipeline: Extracts food items and weights from text.
        Returns (items_list, meal_id).
        """
        self.foodbank_cache.clear()
        
        # Voice correction is now handled internally by the 'main' prompt's PHONETIC NORMALIZATION rule
        prompt = self.prompts['extraction']['main'].format(
            text=text, 
            user_memory=self._get_user_memory(),
            meal_type=meal_type
        )
        resp = await safe_acompletion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            api_base=Config.LITELLM_API_BASE,
            temperature=0.0
        )
        try:
            data = json.loads(resp.choices[0].message.content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in extract_items: {e}")
            data = {}


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

        for item in items_list:
            grams = float(item.get('grams') or 0)
            if grams <= 0.0:
                grams = 100.0
            item['grams'] = grams

        items_list = self._deduplicate_items(items_list)
        
        if not items_list and text.strip():
            items_list = [{"name": text.strip(), "grams": 100.0}]
        
        meal_id = f"meal_{uuid.uuid4().hex[:8]}"
        return items_list, meal_id

    async def resolve_nutrition(self, items_list: List[dict], meal_id: str) -> FoodLog:
        """
        Phase 2 of Async Pipeline: Resolves nutritional data for the items.
        """
        return await self._resolve_and_build_log(items_list, meal_id)

    async def parse(self, text: str, meal_id: str = "unknown", is_voice: bool = False) -> FoodLog:
        # Backward compatibility: uses the new decoupled methods
        items, mid = await self.extract_items(text, is_voice)
        actual_id = meal_id if meal_id != "unknown" else mid
        return await self.resolve_nutrition(items, actual_id)

