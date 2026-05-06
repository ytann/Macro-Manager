import sqlite3
import json
import litellm
import requests

litellm.api_base = "http://localhost:11434"

def get_connection():
    """Returns a connection to the foodbank SQLite database."""
    return sqlite3.connect('foodbank.db')

def seed_db():
    """
    Initializes the foodbank database with a set of starter foods and recipes.
    Creates an FTS5 virtual table for efficient alias-based searching.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS foods")
    cursor.execute("DROP TABLE IF EXISTS recipes")
    cursor.execute("""
        CREATE VIRTUAL TABLE foods USING fts5(
            name, 
            aliases, 
            calories UNINDEXED, 
            protein UNINDEXED, 
            carbs UNINDEXED, 
            fat UNINDEXED, 
            fiber UNINDEXED, 
            is_complete_protein UNINDEXED
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            dish_name TEXT PRIMARY KEY,
            recipe_json TEXT NOT NULL
        )
    """)
    
    foods = [
        ('Rice', 'chawal', 130, 2.7, 28, 0.3, 0.4, 0),
        ('Lentils', 'dal daal pulses', 116, 9, 20, 1, 8, 0),
        ('Red Spinach', 'laal bhaji lal math amaranth leaves', 23, 3, 4, 0, 2, 0),
        ('Paneer', 'cottage cheese', 265, 14, 1.2, 20, 0, 1),
        ('Roti', 'chapati phulka flatbread', 297, 9, 46, 8, 9, 0),
        ('Bhetki', 'barramundi asian seabass', 108, 20, 0, 3, 0, 1),
        ('Chicken Breast', 'murgh', 165, 31, 0, 3.6, 0, 1),
        ('Apple', 'seb', 52, 0.3, 14, 0.2, 2.4, 0),
        ('Penne Pasta', 'pasta macaroni', 131, 5, 25, 0.6, 2.5, 0),
        ('Heavy Cream', 'cream', 340, 2, 3, 35, 0, 0),
        ('Parmesan Cheese', 'parmesan', 431, 38, 4, 29, 0, 1),
        ('Butter', 'makkhan', 717, 0.9, 0.1, 81, 0, 0),
    ]
    
    cursor.executemany("INSERT INTO foods VALUES (?, ?, ?, ?, ?, ?, ?, ?)", foods)
    conn.commit()
    conn.close()

def search_food(query_string):
    """
    Searches for a food item by name or alias.
    Tries exact match first, then FTS5 tokenized search.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Try 1: Exact match on name or aliases
    cursor.execute("SELECT * FROM foods WHERE name = ? OR aliases LIKE ? LIMIT 1", (query_string, f"%{query_string}%"))
    row = cursor.fetchone()
    
    # Try 2: FTS5 Match with tokenization
    if not row:
        # Sanitize query: remove FTS5 special characters that cause syntax errors
        # Keep alphanumeric and spaces
        sanitized = "".join(c for c in query_string if c.isalnum() or c.isspace())
        
        # Replace spaces with * to handle multi-word queries in FTS5
        search_query = " ".join([f"{word}*" for word in sanitized.split()])
        
        if search_query:
            cursor.execute("SELECT * FROM foods WHERE foods MATCH ? ORDER BY rank LIMIT 1", (search_query,))
            row = cursor.fetchone()
            
            # Fallback: Try searching for each word individually if no match found
            if not row:
                for word in sanitized.split():
                    cursor.execute("SELECT * FROM foods WHERE foods MATCH ? ORDER BY rank LIMIT 1", (f"{word}*",))
                    row = cursor.fetchone()
                    if row: break
        
    conn.close()
    
    if row:
        return dict(row)
    return None

def get_recipe(dish_name):
    """
    Retrieves a recipe for a complex dish from the database.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT recipe_json FROM recipes WHERE dish_name = ?", (dish_name.lower(),))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None

def save_recipe(dish_name, recipe_json):
    """
    Saves a learned recipe for a complex dish.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO recipes (dish_name, recipe_json) VALUES (?, ?)",
        (dish_name.lower(), json.dumps(recipe_json))
    )
    conn.commit()
    conn.close()

def search_web_for_food(dish_name):
    """
    Searches DuckDuckGo for nutrition/recipe info and uses LLM to extract data.
    """
    print(f"Searching web for {dish_name}...")
    
    # Try multiple search queries for better coverage
    queries = [
        f"{dish_name} nutrition facts per 100g",
        f"average calories protein carbs fat for {dish_name}",
        f"{dish_name} recipe ingredients weights"
    ]
    
    for query in queries:
        search_url = f"https://html.duckduckgo.com/html/?q={query}"
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            response = requests.get(search_url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue
            
            content = response.text
            extract_prompt = f"""
            The following is HTML content from a search for '{dish_name}'. 
            Extract the SPECIFIC nutrition macros per 100g (calories, protein, carbs, fat, fiber) for this exact item.
            
            CRITICAL: Do not provide generic "average" values for a category of food. If this is a regional dish (like Misal Pav vs Pav Bhaji), ensure the macros reflect the specific ingredients of THAT dish. 
            If it's a complex dish, try to find a recipe (list of ingredients and their weights).
            
            Return a JSON object with:
            - 'type': 'ingredient' or 'dish'
            - 'macros': {{ 'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0 }} (if ingredient)
            - 'recipe': [{{ 'name': '...', 'grams': 0 }}] (if dish)
            - 'total_weight': 0 (if dish)
            - 'reasoning': 'Briefly explain why these values are specific to {dish_name}'
            
            If you cannot find reliable data in this specific HTML, return {{ 'error': 'not found' }}.
            Respond ONLY with JSON.
            
            HTML:
            {content[:10000]} 
            """
            
            resp = litellm.completion(
                model="ollama/llama3.1:latest",
                messages=[{"role": "user", "content": extract_prompt}],
                response_format={"type": "json_object"},
                api_base=litellm.api_base
            )
            data = json.loads(resp.choices[0].message.content)
            if 'error' not in data:
                return data
        except Exception as e:
            print(f"Search attempt failed for {query}: {e}")
            
    return None


def fetch_and_save_recipe(dish_name):
    """
    Uses web search to find if a food is a complex dish, fetches its recipe, and saves it.
    Returns the recipe and total weight if found, otherwise None.
    """
    web_data = search_web_for_food(dish_name)
    if not web_data or 'error' in web_data:
        return None, None
    
    if web_data.get('type') == 'dish' and web_data.get('recipe'):
        recipe = web_data['recipe']
        save_recipe(dish_name, recipe)
        return recipe, web_data.get('total_weight', 500)
    
    return None, None

def add_learned_food(name, calories, protein, carbs, fat, fiber):
    """
    Persists a new food item learned from the LLM into the database.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO foods (name, aliases, calories, protein, carbs, fat, fiber) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, name.lower(), calories, protein, carbs, fat, fiber)
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed_db()
    print(search_food("rice"))
