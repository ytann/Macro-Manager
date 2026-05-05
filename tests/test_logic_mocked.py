import os
from unittest.mock import patch
from database import init_db, save_meal, get_todays_macros
from parser import parse_food_log
import foodbank

def test_logic_mocked():
    print("Resetting DB...")
    if os.path.exists("macros.db"):
        os.remove("macros.db")
    init_db()
    
    print("Seeding Foodbank...")
    foodbank.seed_db()
    
    # Mock litellm.completion to return a valid JSON response immediately
    mock_response = type('obj', (object,), {
        'choices': [
            type('obj', (object,), {
                'message': type('obj', (object,), {
                    'content': '{"items": [{"name": "apple", "grams": 100}]}'
                })
            })
        ]
    })

    with patch('litellm.completion', return_value=mock_response):
        test_text = "I ate 1 apple"
        print(f"Parsing (mocked): {test_text}")
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
    test_logic_mocked()
