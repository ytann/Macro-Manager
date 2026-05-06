import sys
import os
sys.path.append(os.getcwd())
from app.services.extraction import ExtractionService
import json

test_cases = [
    {"name": "Guardrail Test", "text": "1 piece boiled egg, 1 plate misal pav, 1 bombay sandwich", "expected_items": ["Egg", "Misal Pav", "Bombay Sandwich"]},
    {"name": "Unknown/Rare Food", "text": "1 plate of dhokla and some thepla", "expected_items": ["Dhokla", "Thepla"]},
    {"name": "Volume Check (Light)", "text": "2 plate sev puri", "expected_items": ["Sev Puri"]},
    {"name": "Volume Check (Heavy)", "text": "2 plate rice", "expected_items": ["Rice"]},
]

def run_tests():
    service = ExtractionService()
    print("🚀 Batch 2: Guardrails & Volume\n")
    print(f"{'Test Case':<25} | {'Status':<10} | {'Calories':<12} | {'Items Found'}")
    print("-" * 70)
    
    for case in test_cases:
        try:
            result = service.parse(case['text'], meal_id="final_test")
            found_names = [i.name.lower() for i in result.items]
            missing = [exp for exp in case['expected_items'] if not any(exp.lower() in fn for fn in found_names)]
            status = "✅ PASS" if not missing else f"⚠️ MISSING: {missing}"
            print(f"{case['name']:<25} | {status:<10} | {result.total_calories:<12.1f} | {', '.join([i.name for i in result.items])}")
        except Exception as e:
            print(f"{case['name']:<25} | ❌ ERROR    | {'N/A':<12} | {e}")

if __name__ == "__main__":
    run_tests()
