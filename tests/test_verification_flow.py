import sys
import os
sys.path.append(os.getcwd())
from app.services.extraction import ExtractionService
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager
import json

def test_verification_and_update():
    db_manager = DatabaseManager()
    foodbank = FoodbankService(db_manager)
    extraction = ExtractionService(foodbank)
    
    test_food = "poha"
    print(f"--- Testing Verification Flow for: {test_food} ---")
    
    # 1. Check initial state
    initial_data = foodbank.search_food(test_food)
    print(f"Initial DB state: {initial_data}")
    
    # 2. Parse a log containing this food
    print(f"Parsing log: '1 plate {test_food}'...")
    extraction.parse(f"1 plate {test_food}", meal_id="verify_test")
    
    # 3. Check final state
    final_data = foodbank.search_food(test_food)
    print(f"Final DB state: {final_data}")
    
    if final_data and final_data.get('verified') == 1:
        print("✅ SUCCESS: Food item was verified and flag updated to 1.")
    else:
        print("❌ FAILURE: Food item was not verified.")

if __name__ == "__main__":
    test_verification_and_update()
