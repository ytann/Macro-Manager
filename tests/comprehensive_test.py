import sys
import os
sys.path.append(os.getcwd())
from app.services.extraction import parse_food_log
import json

test_cases = [
    {
        "name": "Simple Mixed",
        "text": "2 boiled eggs and an apple"
    },
    {
        "name": "Regional Complex",
        "text": "1 plate misal pav and 1 glass of lassi"
    },
    {
        "name": "Mixed Quantities",
        "text": "1 piece of puran poli, 200g chicken breast, and 1 bowl of dal"
    },
    {
        "name": "Ambiguous/Regional",
        "text": "1 plate pani puri and a piece of jalebi"
    },
    {
        "name": "Multiple Items/Flaky Test",
        "text": "1 plate poha, 1 glass of milk, 2 eggs, and a small bowl of curd"
    },
    {
        "name": "Very Specific/Rare",
        "text": "1 plate of dhokla and some thepla"
    }
]

def run_tests():
    print("🚀 Starting Comprehensive Tests with llama3.1:latest\n")
    for case in test_cases:
        print(f"--- Test: {case['name']} ---")
        print(f"Input: {case['text']}")
        try:
            result = parse_food_log(case['text'], meal_id="comprehensive_test")
            
            print(f"Total Calories: {result.total_calories:.2f} kcal")
            print(f"Macros: P: {result.total_macros.protein:.2f}g, C: {result.total_macros.carbs:.2f}g, F: {result.total_macros.fat:.2f}g")
            print("Items:")
            for item in result.items:
                print(f"  - {item.name}: {item.grams}g | {item.cals:.1f} kcal")
            print("\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")

if __name__ == "__main__":
    run_tests()
