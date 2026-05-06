from app import foodbank
from app import parser

def test_pipeline():
    print("Seeding database...")
    foodbank.seed_db()
    
    test_text = "Had 200g of chicken breast and 100g of white rice"
    print(f"Parsing text: {test_text}")
    
    try:
        result = parser.parse_food_log(test_text, meal_id="test_meal_01")
        print("\nResult:\n", result.model_dump_json(indent=2))
        
        # Expected:
        # Chicken (200g): cal=330, p=62, c=0, f=7.2
        # Rice (100g): cal=130, p=2.7, c=28, f=0.3
        # Total: cal=460, p=64.7, c=28, f=7.5
        
        expected_cal = 460.0
        actual_cal = result.total_calories
        
        if abs(actual_cal - expected_cal) < 0.1:
            print("\n✅ Pipeline Test Passed: Calories match.")
        else:
            print(f"\n❌ Pipeline Test Failed: Expected {expected_cal}, got {actual_cal}")
            
    except Exception as e:
        print(f"\n❌ Error during pipeline execution: {e}")

if __name__ == "__main__":
    test_pipeline()
