import sqlite3
import json
import httpx
import litellm
import yaml
import asyncio
from typing import Optional, List, Dict
from app.services.database import DatabaseManager
from app.core.config import Config

class FoodbankService:
    """
    Manages food nutrition data, learning from LLM/Web, and complex dish recipes.
    """
    MAX_RETRIES = 5

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.prompts = self._load_prompts()
        litellm.api_base = Config.LITELLM_API_BASE
        self.model = Config.LLM_MODEL
        self.http_client = httpx.AsyncClient(timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        self._l1_cache = {}

    def _load_prompts(self) -> Dict:
        with open(Config.PROMPTS_PATH, 'r') as f:
            return yaml.safe_load(f)['foodbank']

    async def _is_network_available(self) -> bool:
        try:
            await self.http_client.head("https://1.1.1.1", timeout=1.5)
            return True
        except (httpx.RequestError, httpx.TimeoutException):
            return False

    async def _fetch_web_page(self, query: str) -> Optional[str]:
        print("Fetching DuckDuckGo...")
        search_url = f"https://html.duckduckgo.com/html/?q={query}"
        try:
            response = await self.http_client.get(search_url)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            print(f"Fetch failed for {query}: {e}")
        return None

    async def queue_for_verification(self, name: str):
        def _queue():
            try:
                conn = self.db.get_foodbank_conn()
                conn.execute(
                    "INSERT OR REPLACE INTO pending_verification (name, retry_count) VALUES (?, COALESCE((SELECT retry_count FROM pending_verification WHERE name = ?), 0))",
                    (name, name)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"DEBUG: SQLite INSERT failed in queue_for_verification: {e}")
        await asyncio.to_thread(_queue)

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

    async def search_web_for_food(self, dish_name: str, html_content: Optional[str] = None) -> Optional[Dict]:
        if html_content:
            try:
                extract_prompt = self.prompts['web_search'].format(dish_name=dish_name, content=html_content[:10000])
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
                print(f"Initial web extraction failed for {dish_name}: {e}")

        queries = [
            f"{dish_name} nutrition facts per 100g",
            f"average calories protein carbs fat for {dish_name}",
            f"{dish_name} recipe ingredients weights"
        ]
        for query in queries:
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            try:
                print("Fetching DuckDuckGo...")
                response = await self.http_client.get(search_url)
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

    async def upsert_food(self, name: str, calories: float, protein: float, carbs: float, fat: float, fiber: float, verified: int = 0, source: Optional[str] = None):
        def _upsert():
            conn = self.db.get_foodbank_conn()
            conn.execute(
                "INSERT OR REPLACE INTO foods (rowid, name, aliases, calories, protein, carbs, fat, fiber, is_complete_protein, verified, source) VALUES ((SELECT rowid FROM foods WHERE name = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (name, name, name.lower(), calories, protein, carbs, fat, fiber, 0, verified, source)
            )
            conn.commit()
            conn.close()
        await asyncio.to_thread(_upsert)

    async def get_nutrition_data(self, name: str) -> Optional[Dict]:
        cache_key = name.lower().strip()
        if cache_key in self._l1_cache:
            print(f'⚡ [CACHE HIT] L1 In-Memory: {name}')
            return self._l1_cache[cache_key]
        
        result = await self._get_nutrition_data_core(name)
        if result is not None:
            self._l1_cache[cache_key] = result
        return result

    async def _get_nutrition_data_core(self, name: str) -> Optional[Dict]:
        # Step A: Query local DB
        food_data = await self.search_food(name)
        
        # Step B: Network check
        is_online = await self._is_network_available()
        
        # Step C: IF OFFLINE
        if not is_online:
            if food_data:
                if food_data.get('verified') == 0:
                    await self.queue_for_verification(name)
                return food_data
            
            # Use internal_estimate as fallback
            estimate_prompt = self.prompts['internal_estimate'].format(name=name)
            try:
                resp = await litellm.acompletion(
                    model=self.model,
                    messages=[{"role": "user", "content": estimate_prompt}],
                    response_format={"type": "json_object"},
                    api_base=Config.LITELLM_API_BASE
                )
                est_data = json.loads(resp.choices[0].message.content)
                if 'error' not in est_data:
                    is_real = est_data.get('is_real_food', False)
                    if isinstance(is_real, str):
                        is_real = is_real.lower() == 'true'
                    if is_real:
                        await self.queue_for_verification(name)
                    
                    c = float(est_data.get('calories') or 0)
                    p = float(est_data.get('protein') or 0)
                    ca = float(est_data.get('carbs') or 0)
                    f = float(est_data.get('fat') or 0)
                    fi = float(est_data.get('fiber') or 0)
                    await self.upsert_food(name, c, p, ca, f, fi, verified=0, source="internal_estimate")
                    return {'calories': c, 'protein': p, 'carbs': ca, 'fat': f, 'fiber': fi}
            except Exception as e:
                print(f"Internal estimate failed for {name} (offline): {e}")
            return None

        # Step D: IF ONLINE
        if food_data and food_data.get('verified') == 1:
            return food_data
        
        # Food is missing or unverified -> Web Search
        # Fetch HTML once to avoid redundant requests
        query = f"nutrition facts {name} per 100g calories protein carbs fat fiber"
        html = await self._fetch_web_page(query)

        # Try find_source_of_truth first (highest quality)
        truth = await self.find_source_of_truth(name, html_content=html)
        if truth and 'error' not in truth:
            # find_source_of_truth already upserts to DB with verification status based on confidence
            return truth
        
        # Fallback to search_web_for_food (will try the same HTML first, then its own queries)
        web_data = await self.search_web_for_food(name, html_content=html)
        if web_data and 'error' not in web_data:
            c = float(web_data.get('calories') or 0)
            p = float(web_data.get('protein') or 0)
            ca = float(web_data.get('carbs') or 0)
            f = float(web_data.get('fat') or 0)
            fi = float(web_data.get('fiber') or 0)
            # Strictly save with verified=1 as per blueprint
            await self.upsert_food(name, c, p, ca, f, fi, verified=1, source="web_search")
            return {'calories': c, 'protein': p, 'carbs': ca, 'fat': f, 'fiber': fi}
        
        # Web search completely failed -> Fallback to internal_estimate
        estimate_prompt = self.prompts['internal_estimate'].format(name=name)
        try:
            resp = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": estimate_prompt}],
                response_format={"type": "json_object"},
                api_base=Config.LITELLM_API_BASE
            )
            est_data = json.loads(resp.choices[0].message.content)
            if 'error' not in est_data:
                is_real = est_data.get('is_real_food', False)
                if isinstance(is_real, str):
                    is_real = is_real.lower() == 'true'
                if is_real:
                    await self.queue_for_verification(name)
                
                c = float(est_data.get('calories') or 0)
                p = float(est_data.get('protein') or 0)
                ca = float(est_data.get('carbs') or 0)
                f = float(est_data.get('fat') or 0)
                fi = float(est_data.get('fiber') or 0)
                await self.upsert_food(name, c, p, ca, f, fi, verified=0, source="internal_estimate")
                return {'calories': c, 'protein': p, 'carbs': ca, 'fat': f, 'fiber': fi}
        except Exception as e:
            print(f"Internal estimate failed for {name} (online fallback): {e}")
        
        return None

    async def find_source_of_truth(self, dish_name: str, html_content: Optional[str] = None, upsert: bool = True) -> Optional[Dict]:
        print(f"🔍 Finding Source of Truth for: {dish_name}...")
        if html_content is None:
            query = f"nutrition facts {dish_name} per 100g calories protein carbs fat fiber"
            html_content = await self._fetch_web_page(query)
        
        if not html_content:
            return None
        
        try:
            truth_prompt = self.prompts['source_of_truth'].format(dish_name=dish_name, content=html_content[:15000])
            resp = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": truth_prompt}],
                response_format={"type": "json_object"},
                api_base=Config.LITELLM_API_BASE
            )
            data = json.loads(resp.choices[0].message.content)
            print(f"Truth search result for {dish_name}: {data}")
            
            if 'error' not in data and upsert:
                conf = data.get('confidence', 'Low')
                is_verified = 1 if conf in ['High', 'Medium'] else 0
                await self.upsert_food(
                    name=dish_name,
                    calories=float(data.get('calories') or 0),
                    protein=float(data.get('protein') or 0),
                    carbs=float(data.get('carbs') or 0),
                    fat=float(data.get('fat') or 0),
                    fiber=float(data.get('fiber') or 0),
                    verified=is_verified,
                    source=data.get('source')
                )
            return data
        except Exception as e:
            print(f"Truth finder failed for {dish_name}: {e}")
        return None

    async def process_verification_queue(self):
        def _get_pending():
            conn = self.db.get_foodbank_conn()
            cursor = conn.execute("SELECT name, retry_count FROM pending_verification")
            rows = cursor.fetchall()
            conn.close()
            return [(row['name'], row['retry_count']) for row in rows]

        pending = await asyncio.to_thread(_get_pending)
        verified_count = 0

        for name, retry_count in pending:
            try:
                if retry_count >= self.MAX_RETRIES:
                    def _remove_stale():
                        conn = self.db.get_foodbank_conn()
                        conn.execute("DELETE FROM pending_verification WHERE name = ?", (name,))
                        conn.commit()
                        conn.close()
                    await asyncio.to_thread(_remove_stale)
                    print(f"Removed stale item: {name} (retries exhausted)")
                    continue

                def _inc_retry():
                    conn = self.db.get_foodbank_conn()
                    conn.execute("UPDATE pending_verification SET retry_count = retry_count + 1 WHERE name = ?", (name,))
                    conn.commit()
                    conn.close()
                await asyncio.to_thread(_inc_retry)

                truth = await self.find_source_of_truth(name, upsert=False)

                if truth and 'error' not in truth:
                    conf = truth.get('confidence', 'Low')
                    if conf in ['High', 'Medium']:
                        await self.upsert_food(
                            name=name,
                            calories=float(truth.get('calories') or 0),
                            protein=float(truth.get('protein') or 0),
                            carbs=float(truth.get('carbs') or 0),
                            fat=float(truth.get('fat') or 0),
                            fiber=float(truth.get('fiber') or 0),
                            verified=1,
                            source=truth.get('source')
                        )
                        def _remove():
                            conn = self.db.get_foodbank_conn()
                            conn.execute("DELETE FROM pending_verification WHERE name = ?", (name,))
                            conn.commit()
                            conn.close()
                        await asyncio.to_thread(_remove)
                        verified_count += 1
                        print(f"Verified: {name}")
                    else:
                        print(f"Low confidence for {name}, retries: {retry_count + 1}/{self.MAX_RETRIES}")
                else:
                    print(f"No data for {name}, retries: {retry_count + 1}/{self.MAX_RETRIES}")
            except Exception as e:
                print(f"Failed to verify {name}: {e}")

        return verified_count

    async def run_sync_cycle(self):
        verified = await self.process_verification_queue()
        if verified > 0:
            await self.update_sync_timestamp()
            print(f"Sync: {verified} items verified and removed from queue")
        return verified

    async def get_pending_count(self) -> int:
        def _count():
            conn = self.db.get_foodbank_conn()
            count = conn.execute("SELECT COUNT(*) FROM pending_verification").fetchone()[0]
            conn.close()
            return count
        return await asyncio.to_thread(_count)

    async def update_sync_timestamp(self):
        def _update():
            conn = self.db.get_foodbank_conn()
            conn.execute("UPDATE sync_status SET last_sync = datetime('now') WHERE id = 1")
            conn.commit()
            conn.close()
        await asyncio.to_thread(_update)

    async def get_sync_timestamp(self) -> Optional[str]:
        def _get():
            conn = self.db.get_foodbank_conn()
            row = conn.execute("SELECT last_sync FROM sync_status WHERE id = 1").fetchone()
            conn.close()
            return row[0] if row else None
        return await asyncio.to_thread(_get)

    def seed_db(self):
        """Backward compatibility helper for tests to seed initial food data."""
        db_manager = self.db
        with sqlite3.connect(db_manager.foodbank_path) as conn:
            cursor = conn.cursor()
            # We use the same seeding logic as DatabaseManager._init_foodbank
            foods = [
                ('Rice', 'chawal', 130, 2.7, 28, 0.3, 0.4, 0, 0, 'initial_seed'),
                ('Lentils', 'dal daal pulses', 116, 9, 20, 1, 8, 0, 0, 'initial_seed'),
                ('Red Spinach', 'laal bhaji lal math amaranth leaves', 23, 3, 4, 0, 2, 0, 0, 'initial_seed'),
                ('Paneer', 'cottage cheese', 265, 14, 1.2, 20, 0, 1, 0, 'initial_seed'),
                ('Roti', 'chapati phulka flatbread', 297, 9, 46, 8, 9, 0, 0, 'initial_seed'),
                ('Bhetki', 'barramundi asian seabass', 108, 20, 0, 3, 0, 1, 0, 'initial_seed'),
                ('Chicken Breast', 'murgh', 165, 31, 0, 3.6, 0, 1, 0, 'initial_seed'),
                ('Apple', 'seb', 52, 0.3, 14, 0.2, 2.4, 0, 0, 'initial_seed'),
                ('Penne Pasta', 'pasta macaroni', 131, 5, 25, 0.6, 2.5, 0, 0, 'initial_seed'),
                ('Heavy Cream', 'cream', 340, 2, 3, 35, 0, 0, 0, 'initial_seed'),
                ('Parmesan Cheese', 'parmesan', 431, 38, 4, 29, 0, 1, 0, 'initial_seed'),
                ('Butter', 'makkhan', 717, 0.9, 0.1, 81, 0, 0, 0, 'initial_seed'),
            ]
            cursor.executemany("INSERT OR REPLACE INTO foods VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", foods)
            conn.commit()

