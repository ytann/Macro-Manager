import asyncio
import sqlite3
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService

async def run_tests():
    db_manager = DatabaseManager()
    foodbank_service = FoodbankService(db_manager)
    
    test_cases = [
        ("Patta Gobi Matar", "Fuzzy Name Match"),
        ("Cabbage Peas", "Fuzzy Alias Match"),
        ("Home Cooked", "Fuzzy Prep Match"),
        ("I had 150g of Patta Gobi Matar, home cooked", "LLM Preprocessing In-DB"),
        ("Soya chunks masala, soya category", "LLM Hierarchical Filter In-DB"),
        ("I had 200g of some rare Amazonian berry, organic", "LLM Preprocessing Out-of-DB"),
    ]
    
    for query, description in test_cases:
        print(f"Testing: {description} | Query: {query}")
        result = await foodbank_service.search_food(query)
        if result:
            print(f"  Result Found: {result['name']}")
        else:
            print(f"  No Result Found")
        print("-" * 40)

    await foodbank_service.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
