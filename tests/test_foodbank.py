import asyncio
import os
import sqlite3
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService
from app.core.config import Config

async def main():
    db_manager = DatabaseManager()
    service = FoodbankService(db_manager)
    
    test_foods = [
        "Poha", 
        "KFC Zinger Burger", 
        "McDonald's Maharaja Mac", 
        "Air Fried Chicken Breast", 
        "Deep Fried Chicken Breast"
    ]
    
    print(f"{'Food Item':<30} | {'Cals':<6} | {'Prot':<6} | {'Carb':<6} | {'Fat':<6} | {'Verified'}")
    print("-" * 75)
    
    for food in test_foods:
        try:
            data = await service.get_nutrition_data(food)
            if data:
                print(f"{food:<30} | {data.get('calories', 0):<6.1f} | {data.get('protein', 0):<6.1f} | {data.get('carbs', 0):<6.1f} | {data.get('fat', 0):<6.1f} | ?")
            else:
                print(f"{food:<30} | Failed to fetch data")
        except Exception as e:
            print(f"{food:<30} | Error: {e}")
    
    await service.close()

if __name__ == "__main__":
    asyncio.run(main())
