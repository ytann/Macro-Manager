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
from app.services.food_reference import AUTHORITATIVE_SOURCES, RELIABLE_FOOD_DATA, parse_quantity_string
from app.core.config import Config
from app.core import queries
from app.core.logger import logger
from app.core.llm import safe_acompletion

class FoodbankService:
    """
    Manages food nutrition data, learning from LLM/Web, and complex dish recipes.
    """
    MAX_RETRIES = 5

    CATEGORY_PROFILES = {
        'leafy_greens': {'calories': 23.0, 'protein': 2.2, 'carbs': 3.6, 'fat': 0.4, 'fiber': 2.2, 'sugar': 0.5, 'saturated_fat': 0.1, 'unsaturated_fat': 0.3},
        'lean_protein': {'calories': 120.0, 'protein': 23.0, 'carbs': 0.0, 'fat': 3.0, 'fiber': 0.0, 'sugar': 0.0, 'saturated_fat': 1.0, 'unsaturated_fat': 2.0},
        'fatty_protein': {'calories': 250.0, 'protein': 18.0, 'carbs': 0.0, 'fat': 20.0, 'fiber': 0.0, 'sugar': 0.0, 'saturated_fat': 7.0, 'unsaturated_fat': 13.0},
        'grains_starches': {'calories': 350.0, 'protein': 8.0, 'carbs': 75.0, 'fat': 1.0, 'fiber': 3.0, 'sugar': 1.0, 'saturated_fat': 0.2, 'unsaturated_fat': 0.8},
        'fruits': {'calories': 50.0, 'protein': 1.0, 'carbs': 12.0, 'fat': 0.0, 'fiber': 2.0, 'sugar': 8.0, 'saturated_fat': 0.0, 'unsaturated_fat': 0.0},
        'processed_snacks': {'calories': 500.0, 'protein': 5.0, 'carbs': 60.0, 'fat': 25.0, 'fiber': 2.0, 'sugar': 20.0, 'saturated_fat': 10.0, 'unsaturated_fat': 15.0},
        'oils_fats': {'calories': 884.0, 'protein': 0.0, 'carbs': 0.0, 'fat': 100.0, 'fiber': 0.0, 'sugar': 0.0, 'saturated_fat': 15.0, 'unsaturated_fat': 85.0},
        'dairy': {'calories': 100.0, 'protein': 6.0, 'carbs': 7.0, 'fat': 5.0, 'fiber': 0.0, 'sugar': 5.0, 'saturated_fat': 3.0, 'unsaturated_fat': 2.0},
        'vegetables_non_leafy': {'calories': 40.0, 'protein': 2.0, 'carbs': 8.0, 'fat': 0.0, 'fiber': 3.0, 'sugar': 3.0, 'saturated_fat': 0.0, 'unsaturated_fat': 0.0},
        'unknown': {'calories': 100.0, 'protein': 5.0, 'carbs': 10.0, 'fat': 5.0, 'fiber': 1.0, 'sugar': 2.0, 'saturated_fat': 1.0, 'unsaturated_fat': 4.0},
    }

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

    async def _prioritize_tavily_search(self, query: str, food_name: str = "") -> Optional[Dict]:
        """
        Enhanced Tavily search that prioritizes authoritative nutrition sources.
        Returns filtered results from trusted domains.
        """
        try:
            # Build domain-restricted query for Tavily
            domain_query = query
            for source in AUTHORITATIVE_SOURCES[:5]:  # Top 5 sources
                domain_query += f" OR site:{source}"
            
            search_result = await self.tavily_client.search(
                query=domain_query,
                search_depth="advanced",
                max_results=8
            )
            
            results = search_result.get('results', [])
            
            # Filter results to prioritize authoritative sources
            filtered_results = []
            for result in results:
                url_lower = result.get('url', '').lower()
                # Check if URL matches authoritative sources
                for source in AUTHORITATIVE_SOURCES:
                    if source in url_lower:
                        filtered_results.append(result)
                        break
            
            # If no authoritative sources found, use top results
            if not filtered_results:
                filtered_results = results[:3]
            
            logger.info(f"Tavily search for '{food_name}' returned {len(filtered_results)} results from authoritative sources")
            return {
                'query': query,
                'results': filtered_results,
                'count': len(filtered_results)
            }
        except Exception as e:
            logger.error(f"Prioritized Tavily search failed for {food_name}: {e}")
            return None

    async def queue_for_verification(self, name: str):
        await asyncio.to_thread(
            self.db.run_foodbank, 
            queries.PENDING_VERIFICATION_UPSERT, 
            (name, name), 
            commit=True
        )

    async def search_food(self, query_string: str) -> Optional[Dict]:
        return await asyncio.to_thread(self._local_resolution_sync, query_string)

    def _local_resolution_sync(self, query_string: str) -> Optional[Dict]:
        """
        Synchronous resolution logic to minimize thread switches.
        Exact Search -> Fuzzy Match -> Exact Search (of match).
        """
        conn = self.db.get_foodbank_conn()
        cursor = conn.cursor()
        
        # 1. Exact Search
        cursor.execute(queries.FOODS_SEARCH_BY_NAME, (query_string, f"%{query_string}%"))
        row = cursor.fetchone()
        
        if not row:
            # 2. Fuzzy Matching Layer
            sanitized = "".join(c for c in query_string if c.isalnum() or c.isspace())
            
            # a. Try search match first
            search_query = " ".join([f"{word}*" for word in sanitized.split()])
            if search_query:
                cursor.execute(queries.FOODS_SEARCH_MATCH, (search_query,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                
                # b. Try individual words
                for word in sanitized.split():
                    cursor.execute(queries.FOODS_SEARCH_MATCH, (f"{word}*",))
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
            
            # c. Fallback to Levenshtein distance over all names
            cursor.execute("SELECT name FROM foods")
            all_names = [r[0] for r in cursor.fetchall()]
            matches = difflib.get_close_matches(query_string, all_names, n=1, cutoff=0.8)
            if matches:
                best_match = matches[0]
                cursor.execute(queries.FOODS_SEARCH_BY_NAME, (best_match, f"%{best_match}%"))
                row = cursor.fetchone()
        
        return dict(row) if row else None

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
                try:
                    data = json.loads(resp.choices[0].message.content)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error in search_web_for_food (initial): {e}")
                    data = {}
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
                try:
                    data = json.loads(resp.choices[0].message.content)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error in search_web_for_food (loop): {e}")
                    data = {}
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
        # Step A: Query local DB (Integrated Exact + Fuzzy Resolution)
        food_data = await self.search_food(name)
        
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
                    messages=[{"role": "user", "content": estimate_prompt}],
                    response_format={"type": "json_object"},
                    api_base=Config.LITELLM_API_BASE
                )
                
                try:
                    est_data = json.loads(resp.choices[0].message.content)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error in _get_nutrition_data_core (offline): {e}")
                    est_data = {}
                
                logger.info(f"Internal estimate result for {name}: {est_data}")
                if 'error' not in est_data:
                    is_real = est_data.get('is_real_food', False)
                    if isinstance(is_real, str):
                        is_real = is_real.lower() == 'true'
                    
                    if not is_real:
                        logger.info(f"Internal estimate flagged {name} as non-food.")
                        return None

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
            
            # Offline Category Fallback
            category_data = await self._get_category_fallback(name)
            if category_data:
                return category_data
                
            return None
        
        # Step D: IF ONLINE
        if food_data and food_data.get('verified') == 1:
            logger.info(f"Using verified local data for {name}")
            return food_data
        
        # Food is missing or unverified -> Web Search
        logger.info(f"Food {name} is missing or unverified. Starting web search.")
        
        # Check if food is in reliable database first (faster fallback)
        name_lower = name.lower().strip()
        for food_key, food_data in RELIABLE_FOOD_DATA.items():
            if food_key in name_lower or name_lower in food_key:
                logger.info(f"Found {name} in reliable database: {food_data}")
                await self.upsert_food(
                    name, 
                    food_data['calories'], 
                    food_data['protein'], 
                    food_data['carbs'], 
                    food_data['fat'], 
                    food_data['fiber'],
                    verified=1,
                    source=food_data.get('source', 'reliable_database')
                )
                return food_data
        
        query = queries.NUTRITION_FACTS_QUERY.format(name=name)
        
        try:
            # Use enhanced Tavily search with authoritative source prioritization
            search_data = await self._prioritize_tavily_search(query, name)
            if search_data and search_data['results']:
                results = search_data['results']
                html = "\n\n".join([f"Source: {r['url']}\nContent: {r['content']}" for r in results[:3]]) if results else None
            else:
                html = None
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
            logger.info(f"Internal estimate result for {name}: {est_data}")
            if 'error' not in est_data:
                is_real = est_data.get('is_real_food', False)
                if isinstance(is_real, str):
                    is_real = is_real.lower() == 'true'
                
                if not is_real:
                    logger.info(f"Internal estimate flagged {name} as non-food (online).")
                    return None

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
        
        # FINAL LINE OF DEFENSE: Category Fallback
        category_data = await self._get_category_fallback(name)
        if category_data:
            # Save it to DB so we don't have to classify it again next time
            await self.upsert_food(
                name=name,
                calories=category_data['calories'],
                protein=category_data['protein'],
                carbs=category_data['carbs'],
                fat=category_data['fat'],
                fiber=category_data['fiber'],
                sugar=category_data['sugar'],
                sat_fat=category_data['saturated_fat'],
                unsat_fat=category_data['unsaturated_fat'],
                verified=0,
                source=category_data['source']
            )
            return category_data
        
        return None



    async def _get_category_fallback(self, name: str) -> Optional[Dict]:
        """Classifies food into a category and returns the average macro profile."""
        logger.info(f"Attempting category fallback for {name}")
        prompt = self.prompts['category_fallback'].format(name=name)
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
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in _get_category_fallback: {e}")
                data = {}
            category = data.get('category')
            
            if category in self.CATEGORY_PROFILES:
                profile = self.CATEGORY_PROFILES[category].copy()
                profile['verified'] = 0
                profile['source'] = f"category_fallback:{category}"
                return profile
            else:
                # Fallback to 'unknown' if LLM returned a category not in our list
                profile = self.CATEGORY_PROFILES['unknown'].copy()
                profile['verified'] = 0
                profile['source'] = "category_fallback:unknown"
                return profile
        except Exception as e:
            logger.error(f"Category fallback failed for {name}: {e}")
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

            try:
                data = json.loads(resp.choices[0].message.content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in find_source_of_truth: {e}")
                data = {}
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
        if not pending:
            return 0
            
        verified_count = 0
        stale_items = []
        items_to_process = []
        
        for name, retry_count in pending:
            if retry_count >= self.MAX_RETRIES:
                stale_items.append((name,))
            else:
                items_to_process.append((name,))

        # Batch delete stale items and increment retries for the rest
        if stale_items:
            await asyncio.to_thread(self.db.run_foodbank_batch, queries.PENDING_VERIFICATION_DELETE, stale_items)
        
        if items_to_process:
            await asyncio.to_thread(self.db.run_foodbank_batch, queries.PENDING_VERIFICATION_INC_RETRY, items_to_process)

        for name, _ in items_to_process:
            try:
                # find_source_of_truth is async (Network/LLM), so it stays as is
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
                        logger.info(f"Low confidence for {name}")
                else:
                        logger.info(f"No data for {name}")
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
            self.db.run_foodbank_batch(sql, params)
        await asyncio.to_thread(_seed)

