import litellm
import json
from app import foodbank
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

litellm.api_base = "http://localhost:11434"

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

def parse_food_log(text: str, meal_id: str = "unknown") -> FoodLog:
    """
    Main entry point for food log parsing. 
    Deconstructs text into ingredients via LLM, fetches macros from Foodbank, 
    and sums total meal nutrition.
    """
    prompt = f"""
    Extract ALL food items and their weights in grams from the text.
    Normalize food names to standard English (e.g., 'spianch' -> 'red spinach').
    If the user inputs a complex dish or meal (e.g., Penne Alfredo, Chicken Tikka Masala, Veggie Pizza), you MUST deconstruct it into its raw base ingredients and estimate the grams for each. (e.g., Penne Alfredo -> penne pasta, heavy cream, parmesan cheese, butter). Do not output the complex name. Only output the base ingredients.
    Return a JSON object with a single key 'items' containing a list of objects.
    Each object must have 'name' and 'grams' keys.
    If weights are given in cups/bowls, convert them to grams based on common food weights.
    
    Example format:
    {{
      "items": [
        {{ "name": "chicken breast", "grams": 200 }},
        {{ "name": "white rice", "grams": 150 }}
      ]
    }}
    
    Text: {text}
    """
    
    response = litellm.completion(
        model="ollama/qwen2.5-coder:7b",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        api_base=litellm.api_base
    )
    
    raw_json = response.choices[0].message.content
    print(f"raw_llm_output: {raw_json}")
    
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
    
    if isinstance(data, dict):
        # 1. Check for known list wrappers
        for key in ['response', 'ingredients', 'data', 'items']:
            if key in data and isinstance(data[key], list):
                items_list = data[key]
                break
        else:
            # 2. If it's a dict with 'name' and 'grams', wrap it
            if "name" in data and "grams" in data:
                items_list = [data]
            else:
                # Fallback to any list found in values
                items_list = next((v for v in data.values() if isinstance(v, list)), [])
    elif isinstance(data, list):
        items_list = data
    else:
        items_list = []

    parsed_items = []
    sum_p, sum_c, sum_f, sum_cal = 0.0, 0.0, 0.0, 0.0

    for item in items_list:
        if not isinstance(item, dict):
            print(f"Skipping invalid item: {item}")
            continue
            
        name = item.get('name')
        grams = item.get('grams', 0)
        
        # 1. Check if it's a known recipe
        recipe = foodbank.get_recipe(name)
        if recipe:
            print(f"Found recipe for {name}. Expanding...")
            # We treat the recipe as a list of ingredients for 1 serving.
            # We scale the recipe by the requested grams vs average serving size.
            # For simplicity, we assume the recipe provided by LLM is for the weight requested
            # OR we scale it. Let's assume the recipe is the "canonical" version and we scale it.
            # If the recipe is for 200g and user wants 400g, we multiply by 2.
            
            # Assume recipe is a list of items with 'name' and 'grams'
            for ingred in recipe:
                # Scale ingred grams based on total recipe weight vs requested grams
                total_recipe_weight = sum(i.get('grams', 0) for i in recipe)
                scale = grams / total_recipe_weight if total_recipe_weight > 0 else 1
                
                ingred_name = ingred.get('name')
                ingred_grams = ingred.get('grams', 0) * scale
                
                # Now look up the base ingredient macros
                food_data = foodbank.search_food(ingred_name)
                if not food_data:
                    print(f"Base ingredient {ingred_name} not found. Learning...")
                    learn_prompt = f"You are a nutrition database. Provide the exact macros for 100g of {ingred_name}. Respond ONLY with a valid JSON object: {{\"calories\": 0, \"protein\": 0, \"carbs\": 0, \"fat\": 0, \"fiber\": 0}}. No markdown, no text."
                    try:
                        learn_resp = litellm.completion(
                            model="ollama/qwen2.5-coder:7b",
                            messages=[{"role": "user", "content": learn_prompt}],
                            response_format={"type": "json_object"},
                            api_base=litellm.api_base
                        )
                        learn_json = json.loads(learn_resp.choices[0].message.content)
                        foodbank.add_learned_food(ingred_name, learn_json.get('calories', 0), learn_json.get('protein', 0), learn_json.get('carbs', 0), learn_json.get('fat', 0), learn_json.get('fiber', 0))
                        food_data = learn_json
                    except Exception as e:
                        print(f"Failed to learn {ingred_name}: {e}")
                        continue
                
                p = (food_data['protein'] / 100) * ingred_grams
                c = (food_data['carbs'] / 100) * ingred_grams
                f = (food_data['fat'] / 100) * ingred_grams
                cal = (food_data['calories'] / 100) * ingred_grams
                sub = SubMacros(
                    fiber=(food_data.get('fiber', 0) / 100) * ingred_grams if food_data.get('fiber') else None,
                    is_complete_protein=bool(food_data.get('is_complete_protein'))
                )
                
                sum_p += p
                sum_c += c
                sum_f += f
                sum_cal += cal
                parsed_items.append(FoodItem(name=ingred_name, grams=ingred_grams, cals=cal, macros=Macros(protein=p, carbs=c, fat=f), sub_macros=sub))
            continue
        
        # 2. Not a known recipe, check if it's a base ingredient
        food_data = foodbank.search_food(name)
        if not food_data:
            # 3. Not in DB, check if it's a complex dish we should learn a recipe for
            print(f"Food {name} not found. Checking if it's a complex dish...")
            recipe_prompt = f"Is '{name}' a complex dish (made of multiple ingredients)? If yes, provide the recipe for a typical serving in JSON: {{\"recipe\": [{{ \"name\": \"ingredient\", \"grams\": 100 }}], \"total_weight\": 500}}. If it's a single ingredient, return {{\"recipe\": null}}. Respond ONLY with JSON. No markdown."
            try:
                recipe_resp = litellm.completion(
                    model="ollama/qwen2.5-coder:7b",
                    messages=[{"role": "user", "content": recipe_prompt}],
                    response_format={"type": "json_object"},
                    api_base=litellm.api_base
                )
                recipe_data = json.loads(recipe_resp.choices[0].message.content)
                if recipe_data.get('recipe'):
                    print(f"Learned new recipe for {name}!")
                    foodbank.save_recipe(name, recipe_data['recipe'])
                    # Now process the recipe
                    for ingred in recipe_data['recipe']:
                        ingred_name = ingred.get('name')
                        # Scale based on requested grams vs recipe total weight
                        total_w = recipe_data.get('total_weight', 500)
                        scale = grams / total_w if total_w > 0 else 1
                        ingred_grams = ingred.get('grams', 0) * scale
                        
                        # Search for base ingredient
                        base_data = foodbank.search_food(ingred_name)
                        if not base_data:
                            # Learn base ingredient macros
                            learn_prompt = f"You are a nutrition database. Provide the exact macros for 100g of {ingred_name}. Respond ONLY with a valid JSON object: {{\"calories\": 0, \"protein\": 0, \"carbs\": 0, \"fat\": 0, \"fiber\": 0}}. No markdown, no text."
                            learn_resp = litellm.completion(
                                model="ollama/qwen2.5-coder:7b",
                                messages=[{"role": "user", "content": learn_prompt}],
                                response_format={"type": "json_object"},
                                api_base=litellm.api_base
                            )
                            learn_json = json.loads(learn_resp.choices[0].message.content)
                            foodbank.add_learned_food(ingred_name, learn_json.get('calories', 0), learn_json.get('protein', 0), learn_json.get('carbs', 0), learn_json.get('fat', 0), learn_json.get('fiber', 0))
                            base_data = learn_json
                        
                        p = (base_data['protein'] / 100) * ingred_grams
                        c = (base_data['carbs'] / 100) * ingred_grams
                        f = (base_data['fat'] / 100) * ingred_grams
                        cal = (base_data['calories'] / 100) * ingred_grams
                        
                        sum_p += p
                        sum_c += c
                        sum_f += f
                        sum_cal += cal
                        parsed_items.append(FoodItem(name=ingred_name, grams=ingred_grams, cals=cal, macros=Macros(protein=p, carbs=c, fat=f), sub_macros=SubMacros(fiber=(base_data.get('fiber', 0) / 100) * ingred_grams if base_data.get('fiber') else None, is_complete_protein=bool(base_data.get('is_complete_protein')))))
                    continue
                else:
                    # It's a single ingredient we just didn't know. Learn it.
                    learn_prompt = f"You are a nutrition database. Provide the exact macros for 100g of {name}. Respond ONLY with a valid JSON object: {{\"calories\": 0, \"protein\": 0, \"carbs\": 0, \"fat\": 0, \"fiber\": 0}}. No markdown, no text."
                    learn_resp = litellm.completion(
                        model="ollama/qwen2.5-coder:7b",
                        messages=[{"role": "user", "content": learn_prompt}],
                        response_format={"type": "json_object"},
                        api_base=litellm.api_base
                    )
                    learn_json = json.loads(learn_resp.choices[0].message.content)
                    foodbank.add_learned_food(name, learn_json.get('calories', 0), learn_json.get('protein', 0), learn_json.get('carbs', 0), learn_json.get('fat', 0), learn_json.get('fiber', 0))
                    food_data = learn_json
            else:
                continue
                
        p = (food_data['protein'] / 100) * grams
        c = (food_data['carbs'] / 100) * grams
        f = (food_data['fat'] / 100) * grams
        cal = (food_data['calories'] / 100) * grams
        sub = SubMacros(
            fiber=(food_data.get('fiber', 0) / 100) * grams if food_data.get('fiber') else None,
            is_complete_protein=bool(food_data.get('is_complete_protein'))
        )
            
        sum_p += p
        sum_c += c
        sum_f += f
        sum_cal += cal
        
        parsed_items.append(FoodItem(
            name=name,
            grams=grams,
            cals=cal,
            macros=Macros(protein=p, carbs=c, fat=f),
            sub_macros=sub
        ))
    
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
