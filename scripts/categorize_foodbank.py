import sqlite3
import json
import logging
import re
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Adjust DB_PATH to be relative to the script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, '..', 'foodbank.db')

# Define the taxonomy and keyword mappings
TAXONOMY = {
    "Poultry": [
        "chicken", "murgh", "murghi", "poulet", "turkey", "duck"
    ],
    "Red Meat": [
        "mutton", "lamb", "beef", "gosht", "boti", "keema", "kheema"
    ],
    "Seafood": [
        "fish", "prawn", "prawns", "shrimp", "crab", "lobster", "calamari", "squid", "bhetki", "rohu"
    ],
    "Egg": [
        "egg", "eggs", "anda"
    ],
    "Pork": [
        "pork", "bacon", "ham", "sausage"
    ],
    "Dairy/Paneer": [
        "paneer", "cheese", "curd", "yogurt", "dahi", "chhena", "milk"
    ],
    "Soya/Tofu": [
        "soya", "soy", "tofu", "tempeh"
    ],
    "Green Veggies": [
        "spinach", "saag", "palak", "broccoli", "beans", "peas", "ladyfinger", "bhindi", "laal bhaji", "lal math"
    ],
    "Starch/Breads": [
        "roti", "naan", "rice", "pasta", "bread", "chawal", "phulka", "chapati", "dal", "daal", "lentils"
    ]
}

def get_category(name: str) -> str:
    """
    Identifies the category of a food item based on its name.
    """
    name_lower = name.lower()
    for category, keywords in TAXONOMY.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', name_lower):
                return category
    return "Other/Misc"

def categorize_foodbank():
    """
    Connects to the foodbank database, fetches all food items,
    determines their category, and updates the new 'category' column.
    """
    if not os.path.exists(DB_PATH):
        logging.error(f"Database not found at {DB_PATH}. Ensure the path is correct.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(foods)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'category' not in columns:
            logging.info("'category' column not found. Adding it now...")
            cursor.execute("ALTER TABLE foods ADD COLUMN category TEXT")
            conn.commit()
            logging.info("Column 'category' added successfully.")

        cursor.execute("SELECT name, aliases FROM foods")
        foods = cursor.fetchall()
        
        if not foods:
            logging.warning("No food items found to categorize.")
            return

        logging.info(f"Found {len(foods)} items to categorize.")
        
        updates = []
        for name, aliases_json in foods:
            category = get_category(name)
            
            if category == "Other/Misc" and aliases_json:
                try:
                    aliases = json.loads(aliases_json)
                    for alias in aliases:
                        alias_cat = get_category(alias)
                        if alias_cat != "Other/Misc":
                            category = alias_cat
                            break
                except (json.JSONDecodeError, TypeError):
                    if isinstance(aliases_json, str):
                        alias_cat = get_category(aliases_json)
                        if alias_cat != "Other/Misc":
                            category = alias_cat
            
            updates.append((category, name))

        if updates:
            logging.info(f"Applying {len(updates)} category updates...")
            cursor.executemany("UPDATE foods SET category = ? WHERE name = ?", updates)
            conn.commit()
            logging.info("Categorization complete.")
        else:
            logging.info("No updates to apply.")

    except sqlite3.Error as e:
        logging.error(f"Database error during categorization: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    categorize_foodbank()
