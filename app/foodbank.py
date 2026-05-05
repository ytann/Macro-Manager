import sqlite3

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
