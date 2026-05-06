import sys
import os
sys.path.append(os.getcwd())
from app.services.extraction import ExtractionService
import json

test_text = "1 plate misal pav and 1 glass of lassi"

def run_test():
    print(f"Testing: {test_text}")
    service = ExtractionService()
    try:
        result = service.parse(test_text, meal_id="final_single_test")
        print(f"Success! Calories: {result.total_calories:.2f}")
        print("Items:", [i.name for i in result.items])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_test()
