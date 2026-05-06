import sqlite3
import json
import httpx
import litellm
import yaml
import asyncio
from typing import Optional, Tuple, List, Dict, Any
from app.services.database import DatabaseManager
from app.core.config import Config

class FoodbankService:
    """
    Manages food nutrition data, learning from LLM/Web, and complex dish recipes.
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.prompts = self._load_prompts()
        litellm.api_base = Config.LITELLM_API_BASE
        self.model = Config.LLM_MODEL

    def _load_prompts(self) -> Dict:
        with open(Config.PROMPTS_PATH, 'r') as f:
            return yaml.safe_load(f)['foodbank']

    async def search_food(self, query_string: str) -> Optional[Dict]:
        def _search():
            conn = self.db.get_foodbank_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM foods WHERE name = ? OR aliases LIKE ? LIMIT 1", (query_string, f"%{query_string}%"))
            row = cursor.fetchone()
            if not row:
                sanitized = "".join(c for c in query_string if c.isalnum() or c.isspace())
                search_query = " ".join([f"{word}*" for word in sanitized.split()])
                if search_query:
                    cursor.execute("SELECT * FROM foods WHERE foods MATCH ? ORDER BY rank LIMIT 1", (search_query,))
                    row = cursor.fetchone()
                    if not row:
                        for word in sanitized.split():
                            cursor.execute("SELECT * FROM foods WHERE foods MATCH ? ORDER BY rank LIMIT 1", (f"{word}*",))
                            row = cursor.fetchone()
                            if row:
                                break
            conn.close()
            return dict(row) if row else None
        return await asyncio.to_thread(_search)

    async def get_recipe(self, dish_name: str) -> Optional[List[Dict]]:
        def _get():
            conn = self.db.get_foodbank_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT recipe_json FROM recipes WHERE dish_name = ?", (dish_name.lower(),))
            row = cursor.fetchone()
            conn.close()
            return json.loads(row[0]) if row else None
        return await asyncio.to_thread(_get)

    async def save_recipe(self, dish_name: str, recipe_json: List[Dict]):
        def _save():
            conn = self.db.get_foodbank_conn()
            conn.execute("INSERT OR REPLACE INTO recipes (dish_name, recipe_json) VALUES (?, ?)", 
                         (dish_name.lower(), json.dumps(recipe_json)))
            conn.commit()
            conn.close()
        await asyncio.to_thread(_save)

    async def search_web_for_food(self, dish_name: str) -> Optional[Dict]:
        queries = [
            f"{dish_name} nutrition facts per 100g",
            f"average calories protein carbs fat for {dish_name}",
            f"{dish_name} recipe ingredients weights"
        ]
        async with httpx.AsyncClient(timeout=10) as client:
            for query in queries:
                search_url = f"https://html.duckduckgo.com/html/?q={query}"
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
                    response = await client.get(search_url, headers=headers)
                    if response.status_code != 200:
                        continue
                    extract_prompt = self.prompts['web_search'].format(dish_name=dish_name, content=response.text[:10000])
                    resp = await litellm.acompletion(
                        model=self.model,
                        messages=[{"role": "user", "content": extract_prompt}],
                        response_format={"type": "json_object"},
                        api_base=Config.LITELLM_API_BASE
                    )
                    data = json.loads(resp.choices[0].message.content)
                    if 'error' not in data:
                        return data
                except Exception as e:
                    print(f"Web search failed for {query}: {e}")
        return None

    async def upsert_food(self, name: str, calories: float, protein: float, carbs: float, fat: float, fiber: float, verified: int = 0):
        def _upsert():
            conn = self.db.get_foodbank_conn()
            conn.execute("DELETE FROM foods WHERE name = ?", (name,))
            conn.execute("INSERT INTO foods (name, aliases, calories, protein, carbs, fat, fiber, is_complete_protein, verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (name, name.lower(), calories, protein, carbs, fat, fiber, 0, verified))
            conn.commit()
            conn.close()
        await asyncio.to_thread(_upsert)

    async def get_nutrition_data(self, name: str) -> Optional[Dict]:
        food_data = await self.search_food(name)
        
        if food_data and food_data.get('verified') == 1:
            return food_data

        print(f"🌐 Fetching authoritative data for: {name}...")
        
        truth = await self.find_source_of_truth(name)
        if truth:
            return truth

        web_data = await self.search_web_for_food(name)
        if web_data and 'error' not in web_data:
            macros = web_data.get('macros', {}) if web_data.get('type') == 'ingredient' else web_data
            c = float(macros.get('calories') or 0)
            p = float(macros.get('protein') or 0)
            ca = float(macros.get('carbs') or 0)
            f = float(macros.get('fat') or 0)
            fi = float(macros.get('fiber') or 0)
            await self.upsert_food(name, c, p, ca, f, fi, verified=0)
            return {'calories': c, 'protein': p, 'carbs': ca, 'fat': f, 'fiber': fi}

        estimate_prompt = self.prompts['foodbank']['internal_estimate'].format(name=name)
        try:
            resp = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": estimate_prompt}],
                response_format={"type": "json_object"},
                api_base=Config.LITELLM_API_BASE
            )
            est_data = json.loads(resp.choices[0].message.content)
            if 'error' not in est_data:
                c = float(est_data.get('calories') or 0)
                p = float(est_data.get('protein') or 0)
                ca = float(est_data.get('carbs') or 0)
                f = float(est_data.get('fat') or 0)
                fi = float(est_data.get('fiber') or 0)
                await self.upsert_food(name, c, p, ca, f, fi, verified=0)
                return {'calories': c, 'protein': p, 'carbs': ca, 'fat': f, 'fiber': fi}
        except Exception as e:
            print(f"Internal estimate failed for {name}: {e}")

        return food_data

    async def find_source_of_truth(self, dish_name: str) -> Optional[Dict]:
        print(f"🔍 Finding Source of Truth for: {dish_name}...")
        query = f"nutrition facts {dish_name} per 100g calories protein carbs fat fiber"
        search_url = f"https://html.duckduckgo.com/html/?q={query}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
                response = await client.get(search_url, headers=headers)
                if response.status_code != 200: return None
                truth_prompt = f"""
                You are a nutrition data validator. From the provided HTML, find the most authoritative 100g nutrition facts for '{dish_name}'.
                
                Prioritize data from: 1. Government health databases, 2. Established nutrition websites, 3. Scientific papers.
                
                Return a JSON object with:
                - 'calories': numeric, 'protein': numeric, 'carbs': numeric, 'fat': numeric, 'fiber': numeric
                - 'source': 'URL or Site Name'
                - 'confidence': 'High', 'Medium', or 'Low'
                
                If the data is contradictory, take the average of the top 3 reputable sources.
                If no reliable data is found, return {{'error': 'not found'}}.
                Respond ONLY with JSON.
                
                HTML:
                {response.text[:15000]}
                """
                resp = await litellm.acompletion(
                    model=self.model,
                    messages=[{"role": "user", "content": truth_prompt}],
                    response_format={"type": "json_object"},
                    api_base=Config.LITELLM_API_BASE
                )
                data = json.loads(resp.choices[0].message.content)
                print(f"Truth search result for {dish_name}: {data}")
                
                if 'error' not in data:
                    conf = data.get('confidence', 'Low')
                    is_verified = 1 if conf in ['High', 'Medium'] else 0
                    await self.upsert_food(
                        name=dish_name,
                        calories=float(data.get('calories') or 0),
                        protein=float(data.get('protein') or 0),
                        carbs=float(data.get('carbs') or 0),
                        fat=float(data.get('fat') or 0),
                        fiber=float(data.get('fiber') or 0),
                        verified=is_verified
                    )
                    return data
        except Exception as e:
            print(f"Truth finder failed for {dish_name}: {e}")
        return None
