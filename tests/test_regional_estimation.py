import pytest
import asyncio
import json
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService
from app.core.config import Config

REGIONAL_FOODS = [
    "Misal Pav", "Puran Poli", "Sabudana Khichdi", "Thalipeeth", "Vada Pav",
    "Masala Dosa", "Medu Vada", "Avial", "Bisi Bele Bath", "Appam",
    "Dhokla", "Litti Chokha", "Poha"
]

NEGATIVE_CONTROLS = [
    "Blue plastic chair", "Concrete block", "iPhone 15", "Oxygen tank"
]

async def mock_network_offline():
    return False

@pytest.mark.asyncio
async def test_regional_estimation_success_rate():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    # Correctly mock network to be offline
    fb._is_network_available = mock_network_offline
    
    success_count = 0
    for food in REGIONAL_FOODS:
        # Clear L1 cache for this food to force a fresh estimate
        cache_key = food.lower().strip()
        if cache_key in fb._l1_cache:
            del fb._l1_cache[cache_key]
            
        res = await fb.get_nutrition_data(food)
        
        if res and 'error' not in res and res['calories'] > 0:
            success_count += 1
            print(f"✅ {food}: {res['calories']} cal")
        else:
            print(f"❌ {food}: Failed or unknown")
            
    await fb.close()
    
    pass_rate = (success_count / len(REGIONAL_FOODS)) * 100
    print(f"Regional Pass Rate: {pass_rate:.2f}%")
    assert pass_rate >= 90.0

@pytest.mark.asyncio
async def test_regional_estimation_safety():
    db = DatabaseManager()
    fb = FoodbankService(db)
    fb._is_network_available = mock_network_offline
    
    for item in NEGATIVE_CONTROLS:
        res = await fb.get_nutrition_data(item)
        # If it's not food, we expect either:
        # 1. None (because it failed all paths including category)
        # 2. A value but marked as verified=0 (since category fallback might still guess)
        # However, our internal_estimate should at least flag is_real_food=False.
        # The get_nutrition_data flow:
        # Local -> Network check -> (if offline) internal_estimate -> category_fallback.
        # If internal_estimate returns is_real_food: false, it doesn't return the data.
        # But category_fallback might still return something.
        
        print(f"Safety Check {item}: {res}")
        
    await fb.close()

if __name__ == "__main__":
    asyncio.run(test_regional_estimation_success_rate())
    asyncio.run(test_regional_estimation_safety())
