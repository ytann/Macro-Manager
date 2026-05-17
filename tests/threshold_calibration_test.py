import asyncio
import re
import random
import time
from typing import Dict, Optional
import sys
import os
import difflib

# Add app root to sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService

# Test Dataset
# Format: (query, [list_of_acceptable_results])
TEST_CASES = {
    "Mutton Saag": ["Mutton", "Red Spinach"],
    "Palak ka Gosht": ["Mutton", "Red Spinach"],
    "Chicken Tikka": ["Chicken Breast"],
    "Fish Curry": ["Bhetki"],
    "Prawn Masala": ["Bhetki"], # Prawn is seafood, Bhetki is the closest seed
    "Paneer Butter Masala": ["Paneer"],
    "Cottage Cheese Tikka": ["Paneer"],
    "Dal Makhani": ["Lentils"],
    "Chawal": ["Rice"],
    "Roti": ["Roti"],
    "Anda Curry": ["Egg"],
    "Soya Chaap": ["Soya Chunks"],
    "Bacon and Eggs": ["Bacon", "Egg"],
    "Saag Chicken (Dry)": ["Chicken Breast", "Red Spinach"],
    "murgh makhani": ["Chicken Breast"],
    "bhetki paturi": ["Bhetki"],
    "chhena poda": ["Paneer"],
    "lal shak": ["Red Spinach"],
}

def clean_and_vary_query(query: str, expected: list):
    """Applies variations to the query."""
    # 1. Regex to remove brackets
    query = re.sub(r'\(.*?\)', '', query).strip()
    
    # 2. Sometimes use only one language term or mix
    words = query.split()
    if len(words) > 1 and random.random() < 0.5:
        # Take a random slice
        start = random.randint(0, len(words) - 1)
        end = random.randint(start + 1, len(words))
        query = " ".join(words[start:end])

    return query, expected

async def run_test(foodbank_service: FoodbankService, query: str, expected_list: list, threshold: float) -> bool:
    """Runs a single test case."""
    result = await foodbank_service._local_resolution_sync(query, threshold=threshold)
    if result:
        # Check if the result name is in the list of acceptable outcomes
        return result.get('name') in expected_list
    return False

async def main():
    """
    Main function to run the threshold calibration test.
    """
    db_manager = DatabaseManager()
    foodbank_service = FoodbankService(db_manager)
    
    # Generate varied test cases
    dataset = [clean_and_vary_query(q, e) for q, e in TEST_CASES.items()]
    total_cases = len(dataset)
    
    print("Starting Threshold Calibration Test...")
    print(f"Total test cases: {total_cases}")
    print("-" * 50)
    print("| Threshold | Correctly Identified | Total Cases | Accuracy |")
    print("|-----------|------------------------|-------------|----------|")

    for i in range(11):
        threshold = 0.4 + i * 0.05
        correctly_identified = 0
        
        start_time = time.time()
        
        tasks = [run_test(foodbank_service, query, expected, threshold) for query, expected in dataset]
        results = await asyncio.gather(*tasks)
        
        correctly_identified = sum(results)
        
        accuracy = (correctly_identified / total_cases) * 100
        
        print(f"| {threshold:.2f}      | {correctly_identified:22} | {total_cases:11} | {accuracy:7.2f}% |")
        
        if accuracy == 100.0:
            print("-" * 50)
            print("Reached 100% accuracy. Early exiting.")
            break
            
    print("-" * 50)
    await foodbank_service.close()

if __name__ == "__main__":
    # Add some dummy data for categories not in the default seed
    db = DatabaseManager()
    conn = db.get_foodbank_conn()
    try:
        conn.execute("INSERT OR IGNORE INTO foods (name, category) VALUES (?, ?)", ("Egg", "Egg"))
        conn.execute("INSERT OR IGNORE INTO foods (name, category) VALUES (?, ?)", ("Soya", "Soya/Tofu"))
        conn.execute("INSERT OR IGNORE INTO foods (name, category) VALUES (?, ?)", ("Bacon", "Pork"))
        conn.commit()
    except Exception as e:
        print(f"Could not insert dummy data: {e}")
    finally:
        conn.close()

    asyncio.run(main())
