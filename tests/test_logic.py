from database import init_db, save_meal, get_todays_macros
from parser import parse_food_log

def test_logic():
    print("Initializing DB...")
    init_db()
    
    test_text = "I ate 1 apple"
    print(f"Parsing: {test_text}")
    try:
        meal_data = parse_food_log(test_text, meal_id="test_01")
        print("Parsed successfully.")
        
        print("Saving meal...")
        save_meal(meal_data)
        print("Saved successfully.")
        
        print("Fetching summary...")
        totals = get_todays_macros()
        print(f"Totals: {totals}")
        
        if totals.get('calories', 0) > 0:
            print("✅ Success: Daily totals updated!")
        else:
            print("❌ Failure: Daily totals are 0!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_logic()
