import sqlite3
import json
import httpx
import litellm
import yaml
import asyncio
import os
import difflib
from tavily import AsyncTavilyClient
from typing import Optional, List, Dict
from app.services.database import DatabaseManager, DEFAULT_FOODS
from app.core.config import Config
from app.core import queries
from app.core.logger import logger
from app.core.llm import safe_acompletion

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
        self.tavily_client = AsyncTavilyClient(api_key=Config.TAVILY_API_KEY)
        self._l1_cache = {}
        self._html_cache = {}

    async def close(self):
        """Closes the shared HTTP client to release resources."""
        await self.http_client.aclose()

    def _load_prompts(self) -> Dict:
        with open(Config.PROMPTS_PATH, 'r') as f:
            return yaml.safe_load(f)['foodbank']

    async def _is_network_available(self) -> bool:
        return True

    async def queue_for_verification(self, name: str):
        await asyncio.to_thread(
            self.db.run_foodbank, 
            queries.PENDING_VERIFICATION_UPSERT, 
            (name, name), 
            commit=True
        )

    async def search_food(self, query_string: str) -> Optional[Dict]:
        def _search():
            # complex logic with multiple attempts, keep as is but use run_foodbank internally if possible
            # actually, since it has multiple steps and loops, keeping the sync function is cleaner
            # but let's see if we can use a sync helper
            conn = self.db.get_foodbank_conn()
            cursor = conn.cursor()
            cursor.execute(queries.FOODS_SEARCH_BY_NAME, (query_string, f"%{query_string}%"))
            row = cursor.fetchone()
            if not row:
                sanitized = "".join(c for c in query_string if c.isalnum() or c.isspace())
                search_query = " ".join([f"{word}*" for word in sanitized.split()])
                if search_query:
                    cursor.execute(queries.FOODS_SEARCH_MATCH, (search_query,))
                    row = cursor.fetchone()
                    if not row:
                        for word in sanitized.split():
                            cursor.execute(queries.FOODS_SEARCH_MATCH, (f"{word}*",))
                            row = cursor.fetchone()
                            if row:
                                break
            return dict(row) if row else None
        return await asyncio.to_thread(_search)

    async def get_recipe(self, dish_name: str) -> Optional[List[Dict]]:
        row = await asyncio.to_thread(
            self.db.run_foodbank, 
            queries.RECIPES_GET_BY_NAME, 
            (dish_name.lower(),), 
            fetchone=True
        )
        return json.loads(row[0]) if row else None

    async def save_recipe(self, dish_name: str, recipe_json: List[Dict]):
        await asyncio.to_thread(
            self.db.run_foodbank, 
            queries.RECIPES_UPSERT, 
            (dish_name.lower(), json.dumps(recipe_json)), 
            commit=True
        )

    async def search_web_for_food(self, dish_name: str, html_content: Optional[str] = None) -> Optional[Dict]:

        if html_content:
            try:
                extract_prompt = self.prompts['web_search'].format(dish_name=dish_name, content=html_content[:10000])
                resp = await safe_acompletion(
                    model=self.model,
                    messages=[{"role": "user", "content": extract_prompt}],
                    response_format={"type": "json_object"},
                    api_base=Config.LITELLM_API_BASE
                )
                data = json.loads(resp.choices[0].message.content)
                if 'error' not in data:
                    return data
            except Exception as e:
                logger.error(f"Initial web extraction failed for {dish_name}: {e}")

        queries_list = [q.format(dish_name=dish_name) for q in queries.WEB_SEARCH_QUERIES]
        for query in queries_list:
            # search_url = queries.DDG_SEARCH_URL.format(query=query)
            try:
                # logger.info("Fetching DuckDuckGo...")
                # response = await self.http_client.get(search_url)
                # if response.status_code != 200:
                #     continue
                search_result = await self.tavily_client.search(query=query, search_depth="advanced")
                results = search_result.get('results', [])
                if not results:
                    continue
                content = "\n\n".join([f"Source: {r['url']}\nContent: {r['content']}" for r in results])
                extract_prompt = self.prompts['web_search'].format(dish_name=dish_name, content=content[:10000])
                resp = await safe_acompletion(
                    model=self.model,
                    messages=[{"role": "user", "content": extract_prompt}],
                    response_format={"type": "json_object"},
                    api_base=Config.LITELLM_API_BASE
                )
                data = json.loads(resp.choices[0].message.content)
                if 'error' not in data:
                    return data
            except Exception as e:
                logger.error(f"Web search failed for {query}: {e}")
        return None

    async def upsert_food(self, name: str, calories: float, protein: float, carbs: float, fat: float, fiber: float, sugar: float = 0.0, sat_fat: float = 0.0, unsat_fat: float = 0.0, verified: int = 0, source: Optional[str] = None, is_complete_protein: int = 0):
        params = (name, name, name.lower(), calories, protein, carbs, fat, fiber, sugar, sat_fat, unsat_fat, is_complete_protein, verified, source)
        await asyncio.to_thread(self.db.run_foodbank, queries.FOODS_UPSERT, params, commit=True)

    async def get_nutrition_data(self, name: str) -> Optional[Dict]:
        cache_key = name.lower().strip()
        if cache_key in self._l1_cache:
            logger.info(f'⚡ [CACHE HIT] L1 In-Memory: {name}')
            return self._l1_cache[cache_key]
        
        result = await self._get_nutrition_data_core(name)
        if result is not None:
            self._l1_cache[cache_key] = result
        return result

    async def _get_nutrition_data_core(self, name: str) -> Optional[Dict]:
        # Step A: Query local DB
        food_data = await self.search_food(name)
        
        # Step A.1: Fuzzy Matching Layer
        if not food_data:
            logger.info(f"No exact match for {name}. Attempting fuzzy match...")
            def _fuzzy_lookup():
                conn = self.db.get_foodbank_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM foods")
                all_names = [row[0] for row in cursor.fetchall()]
                matches = difflib.get_close_matches(name, all_names, n=1, cutoff=0.8)
                return matches[0] if matches else None
            
            best_match = await asyncio.to_thread(_fuzzy_lookup)
            if best_match:
                logger.info(f"Fuzzy match found: {name} -> {best_match}")
                food_data = await self.search_food(best_match)
        
        logger.info(f"Local DB search for {name}: {food_data}")
        
        # Step B: Network check
        is_online = await self._is_network_available()
        logger.info(f"Network status for {name}: {'Online' if is_online else 'Offline'}")
        
        # Step C: IF OFFLINE
        if not is_online:
            if food_data:
                if food_data.get('verified') == 0:
                    await self.queue_for_verification(name)
                return food_data
            
            # Use internal_estimate as fallback
            logger.info(f"Using internal estimate (offline) for {name}")
            estimate_prompt = self.prompts['internal_estimate'].format(name=name)
            try:
                resp = await safe_acompletion(
                    model=self.model,
                    messages=[{"role": "user", "content": extract_prompt}],
                    response_format={"type": "json_object"},
                    api_base=Config.LITELLM_API_BASE
                )

                est_data = json.loads(resp.choices[0].message.content)
                logger.info(f"Internal estimate result for {name}: {est_data}")
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
                    su = float(est_data.get('sugar') or 0)
                    sf = float(est_data.get('saturated_fat') or 0)
                    uf = float(est_data.get('unsaturated_fat') or 0)
                    await self.upsert_food(name, c, p, ca, f, fi, sugar=su, sat_fat=sf, unsat_fat=uf, verified=0, source="internal_estimate")
                    return {'calories': c, 'protein': p, 'carbs': ca, 'fat': f, 'fiber': fi, 'sugar': su, 'saturated_fat': sf, 'unsaturated_fat': uf}
            except Exception as e:
                logger.error(f"Internal estimate failed for {name} (offline): {e}")
            return None
        
        # Step D: IF ONLINE
        if food_data and food_data.get('verified') == 1:
            logger.info(f"Using verified local data for {name}")
            return food_data
        
        # Food is missing or unverified -> Web Search
        logger.info(f"Food {name} is missing or unverified. Starting web search.")
        query = queries.NUTRITION_FACTS_QUERY.format(name=name)
        
        try:
            search_result = await self.tavily_client.search(query=query, search_depth="advanced")
            results = search_result.get('results', [])
            html = "\n\n".join([f"Source: {r['url']}\nContent: {r['content']}" for r in results]) if results else None
        except Exception as e:
            logger.error(f"Tavily search failed for {name}: {e}")
            html = None
        
        # Try find_source_of_truth first (highest quality)
        truth = await self.find_source_of_truth(name)
        if truth and 'error' not in truth:
            logger.info(f"Source of truth found for {name}: {truth}")
            return truth
        
        # Fallback to search_web_for_food (will try the same HTML first, then its own queries)
        web_data = await self.search_web_for_food(name, html_content=html)
        if web_data and 'error' not in web_data:
            c = float(web_data.get('calories') or 0)
            p = float(web_data.get('protein') or 0)
            ca = float(web_data.get('carbs') or 0)
            f = float(web_data.get('fat') or 0)
            fi = float(web_data.get('fiber') or 0)
            su = float(web_data.get('sugar') or 0)
            sf = float(web_data.get('saturated_fat') or 0)
            uf = float(web_data.get('unsaturated_fat') or 0)
            # Strictly save with verified=1 as per blueprint
            await self.upsert_food(name, c, p, ca, f, fi, sugar=su, sat_fat=sf, unsat_fat=uf, verified=1, source="web_search")
            return {'calories': c, 'protein': p, 'carbs': ca, 'fat': f, 'fiber': fi, 'sugar': su, 'saturated_fat': sf, 'unsaturated_fat': uf}

        
        # Web search completely failed -> Fallback to internal_estimate
        logger.info(f"Web search failed for {name}. Falling back to internal estimate.")
        estimate_prompt = self.prompts['internal_estimate'].format(name=name)
        try:
            resp = await safe_acompletion(
                model=self.model,
                messages=[{"role": "user", "content": estimate_prompt}],
                response_format={"type": "json_object"},
                api_base=Config.LITELLM_API_BASE
            )

            est_data = json.loads(resp.choices[0].message.content)
            logger.info(f"Internal estimate result for {name} (online): {est_data}")
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
            logger.error(f"Internal estimate failed for {name} (online fallback): {e}")
        
        return None


    async def find_source_of_truth(self, dish_name: str, upsert: bool = True) -> Optional[Dict]:
        logger.info(f"🔍 Finding Source of Truth for: {dish_name}...")
        try:
            search_result = await self.tavily_client.search(
                query=f"{dish_name} nutrition facts per 100g calories protein carbs fat", 
                search_depth="advanced"
            )
            results = search_result.get('results', [])
            if not results:
                return None
            
            search_context = "\n\n".join([f"Source: {r['url']}\nContent: {r['content']}" for r in results[:3]])
            
            truth_prompt = self.prompts['source_of_truth'].format(dish_name=dish_name, search_context=search_context)
            resp = await safe_acompletion(
                model=self.model,
                messages=[{"role": "user", "content": truth_prompt}],
                response_format={"type": "json_object"},
                api_base=Config.LITELLM_API_BASE
            )

            data = json.loads(resp.choices[0].message.content)
            logger.info(f"Truth search result for {dish_name}: {data}")
            
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
                    sugar=float(data.get('sugar') or 0),
                    sat_fat=float(data.get('saturated_fat') or 0),
                    unsat_fat=float(data.get('unsaturated_fat') or 0),
                    verified=is_verified,
                    source=data.get('source')
                )
            return data
        except Exception as e:
            logger.error(f"Truth finder failed for {dish_name}: {e}")
            return None


    async def process_verification_queue(self):
        def _get_pending():
            return self.db.run_foodbank(queries.PENDING_VERIFICATION_GET_ALL, fetchall=True)

        pending = await asyncio.to_thread(_get_pending)
        verified_count = 0

        for name, retry_count in pending:
            try:
                if retry_count >= self.MAX_RETRIES:
                    await asyncio.to_thread(
                        self.db.run_foodbank, 
                        queries.PENDING_VERIFICATION_DELETE, 
                        (name,), 
                        commit=True
                    )
                    logger.info(f"Removed stale item: {name} (retries exhausted)")
                    continue

                await asyncio.to_thread(
                    self.db.run_foodbank, 
                    queries.PENDING_VERIFICATION_INC_RETRY, 
                    (name,), 
                    commit=True
                )

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
                        await asyncio.to_thread(
                            self.db.run_foodbank, 
                            queries.PENDING_VERIFICATION_DELETE, 
                            (name,), 
                            commit=True
                        )
                        verified_count += 1
                        logger.info(f"Verified: {name}")
                    else:
                        logger.info(f"Low confidence for {name}, retries: {retry_count + 1}/{self.MAX_RETRIES}")
                else:
                        logger.info(f"No data for {name}, retries: {retry_count + 1}/{self.MAX_RETRIES}")
            except Exception as e:
                    logger.error(f"Failed to verify {name}: {e}")

        return verified_count

    async def run_sync_cycle(self):
        verified = await self.process_verification_queue()
        if verified > 0:
            await self.update_sync_timestamp()
            logger.info(f"Sync: {verified} items verified and removed from queue")
        return verified

    async def get_pending_count(self) -> int:
        row = await asyncio.to_thread(
            self.db.run_foodbank, 
            queries.PENDING_VERIFICATION_COUNT, 
            fetchone=True
        )
        return row[0] if row else 0

    async def update_sync_timestamp(self):
        await asyncio.to_thread(
            self.db.run_foodbank, 
            queries.SYNC_STATUS_UPDATE, 
            commit=True
        )

    async def get_sync_timestamp(self) -> Optional[str]:
        row = await asyncio.to_thread(
            self.db.run_foodbank, 
            queries.SYNC_STATUS_GET, 
            fetchone=True
        )
        return row[0] if row else None

    async def seed_db(self):
        """Backward compatibility helper for tests to seed initial food data."""
        def _seed():
            sql = queries.FOODS_UPSERT
            params = [
                (food[0], food[0], food[0].lower(), food[2], food[3], food[4], food[5], food[6], food[7], food[8], food[9])
                for food in DEFAULT_FOODS
            ]
            # Use run_foodbank for the whole list is not directly supported by my current run_foodbank
            # because it doesn't do executemany. I'll use a loop or add executemany to run_foodbank.
            # For now, I'll just use a loop to keep it simple and compatible.
            conn = self.db.get_foodbank_conn()
            conn.executemany(sql, params)
            conn.commit()
        await asyncio.to_thread(_seed)

