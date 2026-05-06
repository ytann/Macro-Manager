import sys
import os
sys.path.append(os.getcwd())
from app.parser import parse_food_log
import json

test_text = "sev puri 2 plates"
print(f"Testing input: {test_text}")

try:
    result = parse_food_log(test_text, meal_id="test_sev_puri")
    print(result.model_dump_json(indent=2))
except Exception as e:
    print(f"Error: {e}")
