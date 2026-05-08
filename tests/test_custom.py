from app.services import foodbank
from app.services import extraction as parser

def test_custom_input():
    print("Seeding database...")
    foodbank.seed_db()
    
    test_text = "I ate 2 cups of rice with 1 bowl of pulses, and 1 cup of red spianch"
    print(f"Parsing text: {test_text}")
    
    try:
        result = parser.parse_food_log(test_text, meal_id="custom_test_01")
        print("\nFinal Result:\n", result.model_dump_json(indent=2))
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_custom_input()
