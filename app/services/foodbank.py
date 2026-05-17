import json
import httpx
import litellm
import yaml
import asyncio
import re
import difflib
from pydantic import BaseModel, Field
from tavily import AsyncTavilyClient
from typing import Optional, List, Dict
from app.services.database import DatabaseManager, DEFAULT_FOODS
from app.services.food_reference import AUTHORITATIVE_SOURCES, RELIABLE_FOOD_DATA
from app.core.config import Config
from app.core import queries
from app.core.logger import logger
from app.core.llm import safe_acompletion

class FoodExtraction(BaseModel):
    """Guardrail for extracted food input."""
    quantity: Optional[str] = Field(None, description="The amount/weight of the food item")
    name: str = Field(..., description="The primary name of the food item")
    food_category: Optional[str] = Field(None, description="The main ingredient category (e.g., poultry, red meat, green veggies)")
    prep_type: Optional[str] = Field(None, description="How the food is prepared (e.g., Home Cooked, Street Style)")
    brand_name: Optional[str] = Field(None, description="The brand of the food product if available")

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
        self.http_client = httpx.AsyncClient(timeout=30, headers={
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

    async def queue_for_enrichment(self, name: str):
        await asyncio.to_thread(
            self.db.run_foodbank, 
            "INSERT OR REPLACE INTO pending_enrichment (name, retry_count) VALUES (?, COALESCE((SELECT retry_count FROM pending_enrichment WHERE name = ?), 0))", 
            (name, name), 
            commit=True
        )

    async def process_enrichment_queue(self):
        def _get_pending():
            return self.db.run_foodbank("SELECT name, retry_count FROM pending_enrichment", fetchall=True)
        
        pending = await asyncio.to_thread(_get_pending)
        if not pending: return 0
        
        enriched_count = 0
        for name, retry_count in pending:
            if retry_count >= self.MAX_RETRIES:
                await asyncio.to_thread(self.db.run_foodbank, "DELETE FROM pending_enrichment WHERE name = ?", (name,), commit=True)
                continue
            
            try:
                # Generate aliases and synonyms via LLM
                prompt = f"Provide a JSON object with 'aliases' (list of common regional/English synonyms) and 'synonyms' (dictionary of word -> [related_words]) for the food item '{name}'. Example: {{\"aliases\": [\"Spinach Mutton\"], \"synonyms\": {{\"Gosht\": [\"Mutton\", \"Lamb\"]}}}}"
                resp = await safe_acompletion(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    api_base=Config.LITELLM_API_BASE
                )
                data = json.loads(resp.choices[0].message.content)
                
                # 1. Update aliases in foods table
                aliases_str = ", ".join(data.get('aliases', []))
                if aliases_str:
                    await asyncio.to_thread(
                        self.db.run_foodbank, 
                        "UPDATE foods SET aliases = aliases || CASE WHEN aliases = '' THEN '' ELSE ', ' END || ? WHERE name = ?", 
                        (aliases_str, name), 
                        commit=True
                    )
                
                # 2. Update global synonym map
                synonyms = data.get('synonyms', {})
                for word, related in synonyms.items():
                    await asyncio.to_thread(
                        self.db.run_foodbank, 
                        "INSERT OR REPLACE INTO synonyms (word, related_words) VALUES (?, ?)", 
                        (word, json.dumps(related)), 
                        commit=True
                    )
                
                await asyncio.to_thread(self.db.run_foodbank, "DELETE FROM pending_enrichment WHERE name = ?", (name,), commit=True)
                enriched_count += 1
            except Exception as e:
                logger.error(f"Enrichment failed for {name}: {e}")
                await asyncio.to_thread(self.db.run_foodbank, "UPDATE pending_enrichment SET retry_count = retry_count + 1 WHERE name = ?", (name,), commit=True)
        
        return enriched_count

    async def search_food(self, query_string: str) -> Optional[Dict]:
        return await self._local_resolution_sync(query_string)

    def identify_category(self, query_string: str) -> Optional[str]:
        """
        Identifies the category of a food item based on keywords in the query.
        """
        query_lower = query_string.lower()
        # This should be defined in a more structured way, maybe from a config file.
        taxonomy = {
            "Poultry": ["chicken", "murgh", "turkey", "duck"],
            "Red Meat": ["mutton", "lamb", "beef", "gosht", "keema"],
            "Seafood": ["fish", "prawn", "shrimp", "crab", "lobster"],
            "Egg": ["egg", "anda"],
            "Pork": ["pork", "bacon", "ham"],
            "Dairy/Paneer": ["paneer", "cheese", "curd", "yogurt"],
            "Soya/Tofu": ["soya", "tofu"],
            "Green Veggies": ["spinach", "saag", "palak", "broccoli", "beans"],
            "Starch/Breads": ["roti", "naan", "rice", "pasta", "bread", "dal"]
        }
        for category, keywords in taxonomy.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', query_lower):
                    return category
        return None

    def expand_query_with_synonyms(self, query_string: str) -> str:
        words = query_string.split()
        expanded_parts = []
        
        conn = self.db.get_foodbank_conn()
        cursor = conn.cursor()
        
        for word in words:
            # Look up synonym map
            cursor.execute("SELECT related_words FROM synonyms WHERE word = ?", (word,))
            row = cursor.fetchone()
            if row:
                related = json.loads(row[0])
                # Create a group: (original OR syn1 OR syn2)
                group = f"({word} {' OR '.join(related)})"
                expanded_parts.append(group)
            else:
                expanded_parts.append(word)
        
        return " AND ".join(expanded_parts)

    async def _local_resolution_sync(self, query_string: str, threshold: float = 0.8) -> Optional[Dict]:
        """
        Input processing system:
        1. Quick Fuzzy Match (Name/Aliases & Prep Type)
        2. LLM Preprocessing -> Hierarchical Filtering (Category) -> Search
        """
        conn = self.db.get_foodbank_conn()
        cursor = conn.cursor()

        # --- Stage 1: Quick Fuzzy Match ---
        # Get all relevant columns for fuzzy matching
        cursor.execute("SELECT name, aliases, preparation_type FROM foods")
        all_foods = cursor.fetchall()
        
        # Fuzzy match with name and aliases
        for name, aliases, prep_type in all_foods:
            # Match name
            if difflib.SequenceMatcher(None, query_string.lower(), name.lower()).ratio() >= threshold:
                cursor.execute(queries.FOODS_SEARCH_BY_NAME, (name, f"%{name}%"))
                return dict(cursor.fetchone())
            
            # Match aliases
            if aliases:
                for alias in aliases.split(','):
                    if difflib.SequenceMatcher(None, query_string.lower(), alias.strip().lower()).ratio() >= threshold:
                        cursor.execute(queries.FOODS_SEARCH_BY_NAME, (name, f"%{name}%"))
                        return dict(cursor.fetchone())

        # Separately fuzzy match with preparation type
        for name, aliases, prep_type in all_foods:
            if prep_type and difflib.SequenceMatcher(None, query_string.lower(), prep_type.lower()).ratio() >= threshold:
                cursor.execute(queries.FOODS_SEARCH_BY_NAME, (name, f"%{name}%"))
                return dict(cursor.fetchone())

        # --- Stage 2: LLM Preprocessing & Hierarchical Filtering ---
        try:
            extraction_prompt = (
                f"Extract food details from the following input: '{query_string}'. "
                "Return a JSON object with: quantity, name, food_category, prep_type, and brand_name. "
                "Food categories should be one of: poultry, red meat, egg, soya, dairy, seafood, green veggies, others."
            )
            resp = await safe_acompletion(
                model=self.model,
                messages=[{"role": "user", "content": extraction_prompt}],
                response_format={"type": "json_object"},
                api_base=Config.LITELLM_API_BASE
            )
            extracted_data = json.loads(resp.choices[0].message.content)
            # Pydantic Guardrail
            extracted = FoodExtraction(**extracted_data)
        except Exception as e:
            logger.error(f"LLM preprocessing failed for {query_string}: {e}")
            return None

        # Hierarchical Filtering: Filter by food category
        if extracted.food_category:
            cursor.execute("SELECT name FROM foods WHERE category = ?", (extracted.food_category,))
            category_candidates = [row[0] for row in cursor.fetchall()]
            
            if category_candidates:
                # Perform fuzzy match within the narrowed search space
                matches = difflib.get_close_matches(extracted.name, category_candidates, n=1, cutoff=threshold)
                if matches:
                    cursor.execute(queries.FOODS_SEARCH_BY_NAME, (matches[0], f"%{matches[0]}%"))
                    return dict(cursor.fetchone())

        return None

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

    async def upsert_food(self, name: str, calories: float, protein: float, carbs: float, fat: float, fiber: float, sugar: float = 0.0, sat_fat: float = 0.0, unsat_fat: float = 0.0, verified: int = 0, source: Optional[str] = None, is_complete_protein: int = 0, reported_qty: float = 100.0, reported_p: float = None, reported_c: float = None, reported_f: float = None, p_per_100: float = None, c_per_100: float = None, f_per_100: float = None, reported_cal: float = None, cal_per_100: float = None, reported_fiber: float = None, fiber_per_100: float = None):
        # Auto-categorize on upsert
        category = self.identify_category(name) or "Other/Misc"
        
        # Default to standard normalization if not provided
        if reported_p is None: reported_p = protein
        if reported_c is None: reported_c = carbs
        if reported_f is None: reported_f = fat
        if p_per_100 is None: p_per_100 = protein
        if c_per_100 is None: c_per_100 = carbs
        if f_per_100 is None: f_per_100 = fat
        if reported_cal is None: reported_cal = calories
        if cal_per_100 is None: cal_per_100 = calories
        if reported_fiber is None: reported_fiber = fiber
        if fiber_per_100 is None: fiber_per_100 = fiber
        
        # Note: The 'category' is not in FOODS_UPSERT query yet. This will be an issue.
        # I need to modify the query in `queries.py`
        params = (name, name, name.lower(), calories, protein, carbs, fat, fiber, sugar, sat_fat, unsat_fat, is_complete_protein, verified, source, category, reported_qty, reported_p, reported_c, reported_f, p_per_100, c_per_100, f_per_100, reported_cal, cal_per_100, reported_fiber, fiber_per_100)
        await asyncio.to_thread(self.db.run_foodbank, queries.FOODS_UPSERT, params, commit=True)

    async def get_nutrition_data(self, name: str) -> Optional[Dict]:
        cache_key = name.lower().strip()
        if cache_key in self._l1_cache:
            item = self._l1_cache[cache_key]
            if item.get('verified') == 1:
                logger.info(f'⚡ [CACHE HIT] L1 In-Memory (Verified): {name}')
                return item
        
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
            qty = web_data.get('weight') or web_data.get('quantity') or 100.0
            await self.normalize_and_upsert(
                name=name, 
                reported_qty=float(qty), 
                protein=p, 
                carbs=ca, 
                fat=f, 
                calories=c, 
                fiber=fi, 
                sugar=su, 
                sat_fat=sf, 
                unsat_fat=uf, 
                verified=1, 
                source="web_search"
            )
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



    async def normalize_and_upsert(self, name: str, reported_qty: float, protein: float, carbs: float, fat: float, calories: Optional[float] = None, fiber: Optional[float] = 0.0, sugar: float = 0.0, sat_fat: float = 0.0, unsat_fat: float = 0.0, source: str = "scan", verified: int = 0) -> bool:
        """
        Normalize reported macros to per 100g and upsert into DB.
        Args:
            name: Food name
            reported_qty: Reported quantity (e.g., 250g)
            protein: Protein in reported quantity (grams)
            carbs: Carbs in reported quantity (grams)
            fat: Fat in reported quantity (grams)
            calories: Calories in reported quantity (optional)
            fiber: Fiber in reported quantity (optional, default 0)
            sugar: Sugar in reported quantity (optional, default 0)
            sat_fat: Saturated fat in reported quantity (optional, default 0)
            unsat_fat: Unsaturated fat in reported quantity (optional, default 0)
            source: Source of data (e.g., 'qr_scan', 'label_scan')
            verified: Set to 1 for user-scanned data
        Returns:
            True if successful, False otherwise
        """
        try:
            if reported_qty <= 0:
                logger.error(f"Invalid reported_qty for {name}: {reported_qty}")
                return False
            
            # Calculate per 100g
            p_per_100 = (protein / reported_qty) * 100
            c_per_100 = (carbs / reported_qty) * 100
            f_per_100 = (fat / reported_qty) * 100
            fiber_per_100 = (fiber / reported_qty) * 100 if fiber is not None else 0.0
            sugar_per_100 = (sugar / reported_qty) * 100
            sat_fat_per_100 = (sat_fat / reported_qty) * 100
            unsat_fat_per_100 = (unsat_fat / reported_qty) * 100
            
            # Calculate calories (assuming standard: 4 cal/g protein, 4 cal/g carbs, 9 cal/g fat)
            if calories is None:
                cal_per_100 = (p_per_100 * 4) + (c_per_100 * 4) + (f_per_100 * 9)
                calories = (protein * 4) + (carbs * 4) + (fat * 9)
            else:
                cal_per_100 = (calories / reported_qty) * 100
            
            logger.info(f"Normalizing {name}: {reported_qty}g reported -> {p_per_100:.2f}g/100g protein, {c_per_100:.2f}g/100g carbs, {f_per_100:.2f}g/100g fat, {cal_per_100:.2f}kcal/100g")
            
            # Upsert into DB with normalized values
            await self.upsert_food(
                name=name,
                calories=cal_per_100,
                protein=p_per_100,
                carbs=c_per_100,
                fat=f_per_100,
                fiber=fiber_per_100,
                sugar=sugar_per_100,
                sat_fat=sat_fat_per_100,
                unsat_fat=unsat_fat_per_100,
                verified=verified,
                source=source,
                reported_qty=reported_qty,
                reported_p=protein,
                reported_c=carbs,
                reported_f=fat,
                p_per_100=p_per_100,
                c_per_100=c_per_100,
                f_per_100=f_per_100,
                reported_cal=calories,
                cal_per_100=cal_per_100,
                reported_fiber=fiber,
                fiber_per_100=fiber_per_100
            )
            
            logger.info(f"✓ Successfully normalized and upserted {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to normalize_and_upsert {name}: {e}")
            return False

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
                is_verified = 1 if conf == 'High' else 0
                qty = data.get('weight') or data.get('quantity') or 100.0
                await self.normalize_and_upsert(
                    name=dish_name,
                    reported_qty=float(qty),
                    protein=float(data.get('protein') or 0),
                    carbs=float(data.get('carbs') or 0),
                    fat=float(data.get('fat') or 0),
                    calories=float(data.get('calories') or 0),
                    fiber=float(data.get('fiber') or 0),
                    sugar=float(data.get('sugar') or 0),
                    sat_fat=float(data.get('sat_fat') or 0),
                    unsat_fat=float(data.get('unsat_fat') or 0),
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
                    if conf == 'High':
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

