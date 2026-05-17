"""
Comprehensive Food Reference Database
Includes reliable macro data and unit-to-gram conversions for global & Indian cuisines.
"""

# ─────────────────────────────────────────────────────────────────────────────
# UNIT CONVERSIONS (quantity descriptor -> grams)
# ─────────────────────────────────────────────────────────────────────────────
UNIT_CONVERSIONS = {
    # Indian bread/flatbread
    "roti": 50,
    "chapati": 50,
    "phulka": 50,
    "wheat roti": 50,
    "naan": 90,
    "butter naan": 95,
    "garlic naan": 95,
    "plain naan": 90,
    "puri": 40,
    "bhature": 150,
    "paratha": 80,
    "aloo paratha": 85,
    "gobi paratha": 85,
    "kulcha": 100,
    "dosa": 150,
    "masala dosa": 160,
    "plain dosa": 140,
    "uttapam": 120,
    "appam": 80,
    "idli": 45,
    "vada": 60,
    "medu vada": 65,
    
    # Rice measurements
    "cup rice": 185,
    "cup cooked rice": 150,
    "bowl rice": 150,
    "spoon rice": 15,
    "tablespoon rice": 15,
    
    # Common pieces/servings
    "piece": 100,
    "slice": 50,
    "serving": 150,
    "cup": 240,
    "bowl": 200,
    "plate": 300,
    
    # Protein/meats (per 100g standard)
    "chicken breast": 100,
    "chicken thigh": 100,
    "fish fillet": 100,
    "egg": 50,
    "paneer piece": 30,
    "tofu": 100,
    "lentil cup": 100,
    
    # Fruits & vegetables (medium/standard)
    "apple": 180,
    "banana": 120,
    "orange": 150,
    "mango": 200,
    "potato": 150,
    "carrot": 80,
    "broccoli cup": 90,
    "spinach cup": 30,
}

# ─────────────────────────────────────────────────────────────────────────────
# AUTHORITATIVE SOURCES FOR TAVILY (Domain Prioritization)
# ─────────────────────────────────────────────────────────────────────────────
AUTHORITATIVE_SOURCES = [
    # Government & Academic
    "usda.gov",
    "nal.usda.gov",
    "fda.gov",
    "nutrition.gov",
    "myfitnesspal.com",
    "cronometer.com",
    "sciencedirect.com",
    "ncbi.nlm.nih.gov",
    
    # Regional nutrition databases
    "niftem.ac.in",  # National Institute of Food Technology Entrepreneurship & Management (India)
    "ifctar.res.in",  # Central Food Technology Research Institute (India)
    "infoods.org",  # International Food Data Systems
    
    # Reputable nutrition websites
    "nutritionix.com",
    "fatsecret.com",
    "caloryking.com",
    "nutritiondata.self.com",
    "eatthismuch.com",
    "livestrong.com",
    
    # Restaurant chains (for accurate branded items)
    "mcdonalds.com",
    "dominos.com",
    "kfc.com",
    "subway.com",
    "taco-bell.com",
    "chipotle.com",
    "pizzahut.com",
    
    # Indian food specific
    "indianfoodcompany.com",
    "archanaskitchen.com",
    "hebbarskitchen.com",
    "swastisrecipes.com",
    "indianhealthyrecipes.com",
    
    # Health & wellness
    "healthline.com",
    "mayoclinic.org",
    "webmd.com",
]

# ─────────────────────────────────────────────────────────────────────────────
# RELIABLE MACRO DATA (per 100g) for Common Foods
# Used as fallback when Tavily search doesn't yield results
# ─────────────────────────────────────────────────────────────────────────────
RELIABLE_FOOD_DATA = {
    # Indian Breads
    "roti": {"calories": 265, "protein": 9, "carbs": 48, "fat": 3, "fiber": 8, "source": "USDA/NIFTEM"},
    "chapati": {"calories": 265, "protein": 9, "carbs": 48, "fat": 3, "fiber": 8, "source": "USDA/NIFTEM"},
    "naan": {"calories": 262, "protein": 9, "carbs": 43, "fat": 3, "fiber": 1.5, "source": "USDA"},
    "paratha": {"calories": 330, "protein": 8, "carbs": 35, "fat": 18, "fiber": 2, "source": "USDA"},
    "dosa": {"calories": 168, "protein": 4.5, "carbs": 30, "fat": 2, "fiber": 1, "source": "IFCTAR"},
    "idli": {"calories": 103, "protein": 2, "carbs": 20, "fat": 0.8, "fiber": 0.5, "source": "IFCTAR"},
    "vada": {"calories": 211, "protein": 7, "carbs": 24, "fat": 9, "fiber": 1, "source": "IFCTAR"},
    "puri": {"calories": 412, "protein": 6, "carbs": 42, "fat": 24, "fiber": 1, "source": "USDA"},
    "bhature": {"calories": 271, "protein": 9, "carbs": 45, "fat": 4, "fiber": 2, "source": "NIFTEM"},
    "uttapam": {"calories": 146, "protein": 4, "carbs": 26, "fat": 1, "fiber": 1, "source": "IFCTAR"},
    
    # Indian Curries & Dishes
    "dal": {"calories": 131, "protein": 9, "carbs": 20, "fat": 0.5, "fiber": 8, "source": "USDA"},
    "sambar": {"calories": 45, "protein": 2, "carbs": 7, "fat": 1, "fiber": 2, "source": "IFCTAR"},
    "rasam": {"calories": 15, "protein": 0.5, "carbs": 3, "fat": 0.2, "fiber": 0.5, "source": "IFCTAR"},
    "aloo gobi": {"calories": 62, "protein": 2, "carbs": 8, "fat": 2.5, "fiber": 2, "source": "NIFTEM"},
    "bhindi sabzi": {"calories": 33, "protein": 2, "carbs": 6, "fat": 0.5, "fiber": 1.5, "source": "USDA"},
    "paneer butter masala": {"calories": 196, "protein": 9, "carbs": 5, "fat": 15, "fiber": 0.5, "source": "NIFTEM"},
    "chole bhature": {"calories": 271, "protein": 10, "carbs": 42, "fat": 5, "fiber": 3, "source": "NIFTEM"},
    "dal makhani": {"calories": 189, "protein": 7, "carbs": 16, "fat": 10, "fiber": 4, "source": "NIFTEM"},
    "butter chicken": {"calories": 196, "protein": 18, "carbs": 5, "fat": 10, "fiber": 0.5, "source": "NIFTEM"},
    "tandoori chicken": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6, "fiber": 0, "source": "USDA"},
    
    # Indian Rice Dishes
    "biryani": {"calories": 263, "protein": 7, "carbs": 39, "fat": 7, "fiber": 0.5, "source": "NIFTEM"},
    "pilaf": {"calories": 289, "protein": 6, "carbs": 47, "fat": 7, "fiber": 0.8, "source": "USDA"},
    "fried rice": {"calories": 162, "protein": 5, "carbs": 27, "fat": 3, "fiber": 1, "source": "NIFTEM"},
    
    # Indian Snacks
    "samosa": {"calories": 262, "protein": 4, "carbs": 32, "fat": 13, "fiber": 2, "source": "NIFTEM"},
    "pakora": {"calories": 321, "protein": 7, "carbs": 30, "fat": 19, "fiber": 1, "source": "NIFTEM"},
    "jalebi": {"calories": 296, "protein": 0.5, "carbs": 75, "fat": 0.2, "fiber": 0, "source": "USDA"},
    "laddu": {"calories": 387, "protein": 7, "carbs": 52, "fat": 17, "fiber": 1, "source": "NIFTEM"},
    "barfi": {"calories": 401, "protein": 9, "carbs": 52, "fat": 18, "fiber": 1, "source": "NIFTEM"},
    "lays chips": {"calories": 536, "protein": 6, "carbs": 56, "fat": 30, "fiber": 3, "source": "USDA"},
    
    # Italian Cuisines
    "pasta": {"calories": 131, "protein": 5, "carbs": 25, "fat": 1.1, "fiber": 1.8, "source": "USDA"},
    "spaghetti": {"calories": 131, "protein": 5, "carbs": 25, "fat": 1.1, "fiber": 1.8, "source": "USDA"},
    "lasagna": {"calories": 161, "protein": 12, "carbs": 18, "fat": 4, "fiber": 1, "source": "USDA"},
    "risotto": {"calories": 194, "protein": 7, "carbs": 33, "fat": 2.5, "fiber": 0.5, "source": "USDA"},
    "pizza": {"calories": 285, "protein": 12, "carbs": 36, "fat": 10, "fiber": 2, "source": "USDA"},
    "pepperoni pizza": {"calories": 285, "protein": 12, "carbs": 36, "fat": 10, "fiber": 2, "source": "USDA"},
    "margherita pizza": {"calories": 271, "protein": 12, "carbs": 35, "fat": 9, "fiber": 2, "source": "USDA"},
    "carbonara": {"calories": 213, "protein": 12, "carbs": 25, "fat": 7, "fiber": 1, "source": "USDA"},
    
    # American Cuisines
    "burger": {"calories": 295, "protein": 17, "carbs": 27, "fat": 14, "fiber": 1.5, "source": "USDA"},
    "cheeseburger": {"calories": 354, "protein": 19, "carbs": 27, "fat": 19, "fiber": 1.5, "source": "USDA"},
    "hot dog": {"calories": 290, "protein": 10, "carbs": 24, "fat": 17, "fiber": 0, "source": "USDA"},
    "fried chicken": {"calories": 320, "protein": 30, "carbs": 9, "fat": 17, "fiber": 0, "source": "USDA"},
    "grilled chicken": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6, "fiber": 0, "source": "USDA"},
    "french fries": {"calories": 365, "protein": 3.4, "carbs": 48, "fat": 17, "fiber": 4.2, "source": "USDA"},
    "mac and cheese": {"calories": 215, "protein": 11, "carbs": 26, "fat": 8, "fiber": 0, "source": "USDA"},
    "meatloaf": {"calories": 265, "protein": 21, "carbs": 6, "fat": 18, "fiber": 0, "source": "USDA"},
    
    # Chinese Cuisines
    "fried rice": {"calories": 162, "protein": 5, "carbs": 27, "fat": 3, "fiber": 1, "source": "USDA"},
    "sweet and sour chicken": {"calories": 197, "protein": 14, "carbs": 22, "fat": 6, "fiber": 0.5, "source": "USDA"},
    "chow mein": {"calories": 199, "protein": 9, "carbs": 21, "fat": 8, "fiber": 1, "source": "USDA"},
    "lo mein": {"calories": 138, "protein": 6, "carbs": 21, "fat": 2.5, "fiber": 1, "source": "USDA"},
    "spring roll": {"calories": 255, "protein": 5, "carbs": 28, "fat": 12, "fiber": 1, "source": "USDA"},
    "kung pao chicken": {"calories": 233, "protein": 17, "carbs": 12, "fat": 12, "fiber": 1, "source": "USDA"},
    
    # Proteins
    "chicken breast": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6, "fiber": 0, "source": "USDA"},
    "salmon": {"calories": 208, "protein": 22, "carbs": 0, "fat": 13, "fiber": 0, "source": "USDA"},
    "egg": {"calories": 155, "protein": 13, "carbs": 1.1, "fat": 11, "fiber": 0, "source": "USDA"},
    "paneer": {"calories": 265, "protein": 25, "carbs": 3.5, "fat": 17, "fiber": 0, "source": "USDA"},
    "tofu": {"calories": 76, "protein": 8, "carbs": 1.9, "fat": 4.8, "fiber": 1.2, "source": "USDA"},
    "lentils": {"calories": 116, "protein": 9, "carbs": 20, "fat": 0.4, "fiber": 8, "source": "USDA"},
    "chickpeas": {"calories": 164, "protein": 9, "carbs": 27, "fat": 2.6, "fiber": 7.6, "source": "USDA"},
    
    # Grains & Starches
    "rice": {"calories": 130, "protein": 2.7, "carbs": 28, "fat": 0.3, "fiber": 0.4, "source": "USDA"},
    "brown rice": {"calories": 111, "protein": 2.6, "carbs": 23, "fat": 0.9, "fiber": 1.8, "source": "USDA"},
    "oats": {"calories": 389, "protein": 17, "carbs": 66, "fat": 7, "fiber": 11, "source": "USDA"},
    "quinoa": {"calories": 120, "protein": 4.4, "carbs": 21, "fat": 1.9, "fiber": 2.8, "source": "USDA"},
    "bread": {"calories": 265, "protein": 9, "carbs": 49, "fat": 3.3, "fiber": 7, "source": "USDA"},
    "whole wheat bread": {"calories": 247, "protein": 13, "carbs": 41, "fat": 3.3, "fiber": 7, "source": "USDA"},
}

def parse_quantity_string(quantity_str: str, food_name: str) -> float:
    """
    Parse quantity string (e.g., '2 rotis', '1 cup rice') to grams.
    
    Args:
        quantity_str: e.g., "2 rotis", "1 cup", "3 pieces"
        food_name: for context-aware conversion
    
    Returns:
        float: estimated grams
    """
    if not quantity_str:
        return 100.0
    
    quantity_lower = quantity_str.lower().strip()
    
    # Try exact match with UNIT_CONVERSIONS
    for unit, grams_per_unit in UNIT_CONVERSIONS.items():
        if unit in quantity_lower:
            try:
                # Extract number from string (e.g., "2 rotis" -> 2)
                import re
                match = re.search(r'(\d+(?:\.\d+)?)', quantity_lower)
                if match:
                    count = float(match.group(1))
                    return count * grams_per_unit
            except:
                pass
    
    # Fallback: if contains a number, default to multiplying by 100
    try:
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', quantity_lower)
        if match:
            return float(match.group(1)) * 100
    except:
        pass
    
    return 100.0  # Default serving size
