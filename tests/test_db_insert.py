from database import init_db, save_meal, get_todays_macros, DB_PATH
import os

def test_db_flow():
    # Cleanup old DB for fresh test
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    init_db()
    
    # Mock FoodLog data matching pydantic_schema_v2.md
    meal_1 = {
        "meal_id": "breakfast_01",
        "items": [
            {
                "name": "Eggs",
                "grams": 100,
                "cals": 155,
                "macros": {"protein": 13, "carbs": 1, "fat": 11},
                "sub_macros": None
            },
            {
                "name": "Toast",
                "grams": 50,
                "cals": 130,
                "macros": {"protein": 4, "carbs": 25, "fat": 1},
                "sub_macros": {"fiber": 2}
            }
        ],
        "confidence_score": 0.9
    }
    
    meal_2 = {
        "meal_id": "lunch_01",
        "items": [
            {
                "name": "Chicken",
                "grams": 200,
                "cals": 330,
                "macros": {"protein": 62, "carbs": 0, "fat": 7},
                "sub_macros": None
            }
        ],
        "confidence_score": 0.95
    }
    
    print("Saving meals...")
    save_meal(meal_1)
    save_meal(meal_2)
    
    print("Fetching totals...")
    totals = get_todays_macros()
    print(f"Totals: {totals}")
    
    # Expected: 
    # Protein: 13 + 4 + 62 = 79
    # Carbs: 1 + 25 + 0 = 26
    # Fat: 11 + 1 + 7 = 19
    # Cals: 155 + 130 + 330 = 615
    
    assert totals["protein"] == 79, f"Protein mismatch: {totals['protein']}"
    assert totals["carbs"] == 26, f"Carbs mismatch: {totals['carbs']}"
    assert totals["fat"] == 19, f"Fat mismatch: {totals['fat']}"
    assert totals["calories"] == 615, f"Calories mismatch: {totals['calories']}"
    
    print("Test PASSED")

if __name__ == "__main__":
    test_db_flow()
