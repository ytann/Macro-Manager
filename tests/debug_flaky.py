import sys
import os
sys.path.append(os.getcwd())
from app.parser import parse_food_log
import json

test_cases = [
    "2 boiled eggs with 1 plate misal pav",
    "1 apple and 2 bananas",
    "1 plate poha, 1 glass of milk, and 2 eggs",
    "some rice and a piece of chicken",
]

def run_tests():
    for text in test_cases:
        print(f"\n--- Testing: {text} ---")
        try:
            result = parse_food_log(text, meal_id="debug_id")
            print(f"Items found: {len(result.items)}")
            for item in result.items:
                print(f"- {item.name} ({item.grams}g)")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_tests()
