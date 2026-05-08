import sys
import os
import inspect
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

def test_find_source_of_truth_hardcoded():
    fb_service = FoodbankService(DatabaseManager())
    source_code = inspect.getsource(fb_service.find_source_of_truth)
    
    # Look for typical hardcoded prompt markers
    # Currently it has a big f-string starting with "You are a nutrition data validator..."
    if "You are a nutrition data validator" in source_code:
        print("❌ FAIL: Found hardcoded prompt string in find_source_of_truth.")
    else:
        print("✅ PASS: No obvious hardcoded prompt string found.")

if __name__ == "__main__":
    test_find_source_of_truth_hardcoded()
