import sys
import os
sys.path.append(os.getcwd())
from app.services.extraction import parse_food_log
import json

test_cases = [
    {"meal": "Breakfast", "text": "1 plate misal pav, 1 plate pav bhaji"},
    {"meal": "Lunch", "text": "1 piece of puran poli"},
    {"meal": "Dinner", "text": "1 plate pani puri, 1 beg salad bowl"},
]

def run_tests():
    for case in test_cases:
        print(f"\n--- Testing {case['meal']}: {case['text']} ---")
        try:
            result = parse_food_log(case['text'], meal_id=f"{case['meal'].lower()}_test")
            print(result.model_dump_json(indent=2))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_tests()
