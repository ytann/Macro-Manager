import litellm
import json
from app import foodbank
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

def deduplicate_items(items: List[dict]) -> List[dict]:
    """
    Removes duplicate food items and filters out non-food quantifiers.
    """
    if not items:
        return []
        
    junk_terms = {'plate', 'bowl', 'glass', 'piece', 'serving', 'portion', 'cup'}
    unique_items = []
    seen_names = set()
    
    for item in items:
        name = item.get('name', '').lower().strip()
        if not name or any(term == name for term in junk_terms):
            continue
            
        # Simple overlap check to avoid "Misal Pav" and "Misal" being both kept
        is_duplicate = False
        for seen in seen_names:
            if name in seen or seen in name:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_items.append(item)
            seen_names.add(name)
            
    return unique_items

class Macros(BaseModel):

    protein: float = Field(..., ge=0)
    carbs: float = Field(..., ge=0)
    fat: float = Field(..., ge=0)

class SubMacros(BaseModel):
    fiber: Optional[float] = Field(None, ge=0)
    is_complete_protein: Optional[bool] = None

class FoodItem(BaseModel):
    name: str
    grams: float = Field(..., ge=0)
    cals: float = Field(..., ge=0)
    macros: Macros
    sub_macros: Optional[SubMacros] = None

class FoodLog(BaseModel):
    meal_id: str
    items: List[FoodItem]
    total_macros: Macros
    total_calories: float
    confidence_score: float = Field(..., ge=0, le=1)

    @field_validator('confidence_score')
    @classmethod
    def validate_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Score must be between 0 and 1')
        return v

def verify_extracted_items(text: str, items: List[dict]) -> List[dict]:
    """
    Guardrail tool to ensure no food items were missed during initial extraction.
    """
    found_details = [f"{i.get('name')} ({i.get('grams')}g)" for i in items]
    verification_prompt = f"""
    Original Text: "{text}"
    Items already extracted: {found_details}
    
    Task: Identify ONLY actual food items, dishes, or ingredients mentioned in the text that are COMPLETELY missing from the extracted list.
    
    CRITICAL RESTRICTIONS:
    1. NO QUANTIFIERS: Never suggest 'plate', 'bowl', 'glass', 'piece', 'portion', 'serving', or numeric quantities (e.g., '2 plates') as food items.
    2. NO OVERLAPS: If an item is already present (e.g., 'Sev Puri' is found), do not suggest parts of it (e.g., 'Sev' or 'Puri').
    3. NUMERIC WEIGHTS: Provide a single numeric weight in grams for any missing item.
    
    Return a JSON object with a key 'missing' containing a list of objects with 'name' (string) and 'grams' (number).
    If nothing is missing, return {{ "missing": [] }}.
    
    Respond ONLY with JSON.
    """
    try:
        resp = litellm.completion(
            model="ollama/llama3.1:latest",
            messages=[{"role": "user", "content": verification_prompt}],
            response_format={"type": "json_object"},
            api_base=litellm.api_base
        )
        data = json.loads(resp.choices[0].message.content)
        return data.get('missing', [])
    except Exception as e:
        print(f"Verification guardrail failed: {e}")
        return []

def parse_food_log(text: str, meal_id: str = "unknown") -> FoodLog:
    """
    Main entry point for food log parsing. 
    Deconstructs text into ingredients via LLM, fetches macros from Foodbank, 
    and sums total meal nutrition.
    """
    prompt = f"""
    You are a precise food extraction engine. Extract ALL food items and their estimated weights in grams from the text.
    
    RULES:
    1. ITEM IDENTIFICATION: Extract only the food name. Remove quantifiers like '1 plate of', 'a bowl of', '2 pieces of'.
    2. WEIGHT ESTIMATION: If weight is not provided, estimate a realistic weight in grams based on the specific food item's typical density and serving size.
       - DO NOT use static ranges for quantifiers. A 'plate' of Sev Puri is significantly lighter than a 'plate' of Rice.
       - Consider the nature of the food: 1 plate of snacks (like Sev Puri) might be 150-250g, while 1 plate of a main meal (like Biryani) might be 400-600g.
       - Typical benchmarks: Single egg ~50g, standard apple ~150g.
    3. REGIONAL FOODS: Preserve names like 'Puran Poli', 'Poha', 'Misal Pav'.
    4. FORMAT: Return a JSON object with a key 'items' containing a list of objects with 'name' and 'grams'.
    
    Text: {text}
    """

    
    response = litellm.completion(
        model="ollama/llama3.1:latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        api_base=litellm.api_base
    )
    
    raw_json = response.choices[0].message.content
    cleaned_json = raw_json.strip()
    if cleaned_json.startswith("```json"):
        cleaned_json = cleaned_json[7:]
    if cleaned_json.endswith("```"):
        cleaned_json = cleaned_json[:-3]
    cleaned_json = cleaned_json.strip()
    
    try:
        data = json.loads(cleaned_json)
    except json.JSONDecodeError as e:
        raise Exception(f"LLM output was not valid JSON: {e}")
    
    items_list = []
    if isinstance(data, dict):
        for key in ['items', 'ingredients', 'data', 'response']:
            if key in data and isinstance(data[key], list):
                items_list = data[key]
                break
        if not items_list:
            for v in data.values():
                if isinstance(v, list):
                    items_list = v
                    break
        if not items_list and "name" in data and "grams" in data:
            items_list = [data]
    elif isinstance(data, list):
        items_list = data

    # Guardrail: Verify if any items were missed
    missing_items = verify_extracted_items(text, items_list)
    if missing_items:
        print(f"Guardrail found missing items: {missing_items}. Merging...")
        for m in missing_items:
            if isinstance(m, dict) and 'name' in m:
                items_list.append(m)
    
    # Clean up and deduplicate
    items_list = deduplicate_items(items_list)



    parsed_items = []
    sum_p, sum_c, sum_f, sum_cal = 0.0, 0.0, 0.0, 0.0

    def process_base_ingredient(name, grams):
        nonlocal sum_p, sum_c, sum_f, sum_cal
        food_data = foodbank.search_food(name)
        if not food_data:
            print(f"Base ingredient {name} not found. Searching web...")
            web_data = foodbank.search_web_for_food(name)
            if web_data and 'error' not in web_data and web_data.get('type') == 'ingredient':
                macros = web_data.get('macros', {})
                calories = float(macros.get('calories') or 0)
                protein = float(macros.get('protein') or 0)
                carbs = float(macros.get('carbs') or 0)
                fat = float(macros.get('fat') or 0)
                fiber = float(macros.get('fiber') or 0)
                
                foodbank.add_learned_food(name, calories, protein, carbs, fat, fiber)
                food_data = {
                    'calories': calories,
                    'protein': protein,
                    'carbs': carbs,
                    'fat': fat,
                    'fiber': fiber
                }
            else:
                # Last resort: Use LLM internal knowledge for items that couldn't be found on the web
                print(f"Web search failed for {name}. Attempting internal knowledge estimate...")
                estimate_prompt = f"""You are a world-class nutrition expert. 
                Provide the standard, specific nutrition macros for 100g of '{name}'.
                
                ANALYSIS GUIDELINES:
                1. Deconstruct '{name}' into its likely core ingredients.
                2. If it is a regional, specialty, or complex dish, calculate the macros based on those typical constituents.
                3. If it is a single ingredient, use scientifically accurate standard values.
                
                Return ONLY a JSON object: {{'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0, 'reasoning': '...'}}. 
                If you are absolutely unsure, return {{'error': 'unknown'}}.
                
                DO NOT return 0 for all fields. Provide a realistic estimate based on food science and typical preparation."""
                try:
                    est_resp = litellm.completion(
                        model="ollama/llama3.1:latest",
                        messages=[{"role": "user", "content": estimate_prompt}],
                        response_format={"type": "json_object"},
                        api_base=litellm.api_base
                    )
                    est_data = json.loads(est_resp.choices[0].message.content)
                    if 'error' not in est_data:
                        calories = float(est_data.get('calories') or 0)
                        protein = float(est_data.get('protein') or 0)
                        carbs = float(est_data.get('carbs') or 0)
                        fat = float(est_data.get('fat') or 0)
                        fiber = float(est_data.get('fiber') or 0)
                        foodbank.add_learned_food(name, calories, protein, carbs, fat, fiber)
                        food_data = {
                            'calories': calories,
                            'protein': protein,
                            'carbs': carbs,
                            'fat': fat,
                            'fiber': fiber
                        }
                    else:
                        print(f"Could not find reliable macros for {name}. Skipping.")
                        return
                except Exception as e:
                    print(f"Internal estimate failed for {name}: {e}")
                    return

        p = (float(food_data.get('protein') or 0) / 100) * grams
        c = (float(food_data.get('carbs') or 0) / 100) * grams
        f = (float(food_data.get('fat') or 0) / 100) * grams
        cal = (float(food_data.get('calories') or 0) / 100) * grams
        sub = SubMacros(
            fiber=(float(food_data.get('fiber') or 0) / 100) * grams if food_data.get('fiber') is not None else None,
            is_complete_protein=bool(food_data.get('is_complete_protein'))
        )
        
        sum_p += p
        sum_c += c
        sum_f += f
        sum_cal += cal
        parsed_items.append(FoodItem(name=name, grams=grams, cals=cal, macros=Macros(protein=p, carbs=c, fat=f), sub_macros=sub))


    for item in items_list:
        if not isinstance(item, dict): continue
        name = item.get('name')
        grams = float(item.get('grams') or 0)
        
        recipe = foodbank.get_recipe(name)
        if recipe:
            print(f"Found recipe for {name}. Expanding...")
            total_recipe_weight = sum(float(i.get('grams') or 0) for i in recipe)
            scale = grams / total_recipe_weight if total_recipe_weight > 0 else 1
            
            # Track macros for the dish itself
            dish_p, dish_c, dish_f, dish_cal = 0.0, 0.0, 0.0, 0.0
            
            # We use a temporary list to avoid adding ingredients to the main list 
            # if we want to represent the dish as a single item.
            # However, to keep the "expansion" logic, we'll process ingredients 
            # but we will also add the dish summary.
            
            # To avoid double counting, we'll use a modified process_base_ingredient 
            # or just calculate manually here.
            
            # Let's just process ingredients and then add the dish summary at the end 
            # by summing what was just added.
            start_idx = len(parsed_items)
            for ingred in recipe:
                ingred_name = ingred.get('name')
                ingred_grams = float(ingred.get('grams') or 0) * scale
                process_base_ingredient(ingred_name, ingred_grams)
            
            # Sum up the ingredients just added for this dish
            recipe_items = parsed_items[start_idx:]
            dish_p = sum(item.macros.protein for item in recipe_items)
            dish_c = sum(item.macros.carbs for item in recipe_items)
            dish_f = sum(item.macros.fat for item in recipe_items)
            dish_cal = sum(item.cals for item in recipe_items)
            
            # Prepend the dish summary as a separate item for visibility in journal
            dish_summary = FoodItem(
                name=f"{name} (Total)", 
                grams=grams, 
                cals=dish_cal, 
                macros=Macros(protein=dish_p, carbs=dish_c, fat=dish_f)
            )
            parsed_items.insert(start_idx, dish_summary)
            continue

        food_data = foodbank.search_food(name)
        if food_data:
            process_base_ingredient(name, grams)
        else:
            print(f"Food {name} not found. Checking if it's a complex dish...")
            recipe, total_w = foodbank.fetch_and_save_recipe(name)
            if recipe:
                print(f"Learned new recipe for {name}!")
                scale = grams / total_w if total_w > 0 else 1
                for ingred in recipe:
                    process_base_ingredient(ingred.get('name'), float(ingred.get('grams') or 0) * scale)
            else:
                process_base_ingredient(name, grams)

    if not parsed_items:
        raise ValueError("LLM failed to extract any valid food items.")
    
    return FoodLog(
        meal_id=meal_id,
        items=parsed_items,
        total_macros=Macros(protein=sum_p, carbs=sum_c, fat=sum_f),
        total_calories=sum_cal,
        confidence_score=1.0
    )

if __name__ == "__main__":
    test_text = "Had 200g of chicken breast and 100g of white rice"
    try:
        result = parse_food_log(test_text, meal_id="lunch_01")
        print(result.model_dump_json(indent=2))
    except Exception as e:
        print(f"Error: {e}")
