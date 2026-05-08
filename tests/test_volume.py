import sys
import os
sys.path.append(os.getcwd())
from app.services.extraction import parse_food_log
import json

test_cases = [
    {"text": "2 plate sev puri"},
    {"text": "2 plate rice"},
]

def run_tests():
    for case in test_cases:
        print(f"\n--- Testing: {case['text']} ---")
        try:
            result = parse_food_log(case['text'], meal_id="volume_test")
            for item in result.items:
                print(f"- {item.name}: {item.grams}g")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_tests()
