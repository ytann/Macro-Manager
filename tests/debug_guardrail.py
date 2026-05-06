import sys
import os
sys.path.append(os.getcwd())
from app.parser import parse_food_log
import json

test_text = "1 piece boiled egg, 1 plate misal pav, 1 bombay sandwich"
print(f"Testing input: {test_text}")

try:
    result = parse_food_log(test_text, meal_id="test_sandwich")
    print(result.model_dump_json(indent=2))
except Exception as e:
    print(f"Error: {e}")
