import sys
import os
sys.path.append(os.getcwd())
from app.parser import parse_food_log
import json

test_cases = [
    {"text": "1 plate pani puri"},
    {"text": "1 plate poha"},
]

def run_tests():
    for case in test_cases:
        print(f"\n--- Testing: {case['text']} ---")
        try:
            result = parse_food_log(case['text'], meal_id="debug_test")
            print(result.model_dump_json(indent=2))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_tests()
