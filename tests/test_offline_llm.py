import asyncio
import sqlite3
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService
from unittest.mock import AsyncMock, patch

async def test_llm_offline_behavior():
    db_manager = DatabaseManager()
    foodbank = FoodbankService(db_manager)
    
    # Mock network to be offline
    foodbank._is_network_available = AsyncMock(return_value=False)
    # Mock search_food to return None to bypass DB lookup and force LLM path
    foodbank.search_food = AsyncMock(return_value=None)
    
    test_cases = [
        {"name": "Avocado", "should_be_real": True, "desc": "Real food"},
        {"name": "Nuclear Space Dust", "should_be_real": False, "desc": "Nonsensical item"},
        {"name": "Uranium-235", "should_be_real": False, "desc": "Hazardous material"},
        {"name": "Invisible Pizza", "should_be_real": False, "desc": "Imaginary food"},
        {"name": "Void Matter", "should_be_real": False, "desc": "Abstract concept"},
        {"name": "Pizza-flavored Soap", "should_be_real": False, "desc": "Non-consumable"},
        {"name": "Liquid Gold", "should_be_real": False, "desc": "Metal"},
        {"name": "Deep Sea Pressure", "should_be_real": False, "desc": "Physical force"},
        {"name": "Cloud Vapor", "should_be_real": False, "desc": "Atmospheric gas"},
        {"name": "Cyber-Sushi 3000", "should_be_real": False, "desc": "Sci-fi item"},
        {"name": "Ancient Dragon Scale", "should_be_real": False, "desc": "Mythical item"},
        {"name": "Quantum Broccoli", "should_be_real": False, "desc": "Impossible food"},
    ]
    
    print("🚀 Starting Pure LLM Stress Test (10+ Nonsensical Items)\n" + "="*70)
    
    for case in test_cases:
        name = case["name"]
        should_be_real = case["should_be_real"]
        
        # Clear pending queue for this item
        def clear_pending():
            conn = db_manager.get_foodbank_conn()
            conn.execute("DELETE FROM pending_verification WHERE name = ?", (name,))
            conn.commit()
            conn.close()
        await asyncio.to_thread(clear_pending)
        
        print(f"Testing: {name: <25} | {case['desc']}")
        
        # Execute the nutrition lookup
        result = await foodbank.get_nutrition_data(name)
        
        # Check if it was queued for verification
        def check_queued():
            conn = db_manager.get_foodbank_conn()
            res = conn.execute("SELECT 1 FROM pending_verification WHERE name = ?", (name,)).fetchone()
            conn.close()
            return res is not None
        
        is_queued = await asyncio.to_thread(check_queued)
        
        if result:
            cals = result.get('calories', 0)
            if should_be_real:
                if cals > 0 and is_queued:
                    print("  ✅ PASS")
                else:
                    print(f"  ❌ FAIL: Expected real food (cals > 0, queued=True), got cals={cals}, queued={is_queued}")
            else:
                if cals == 0 and not is_queued:
                    print("  ✅ PASS")
                else:
                    print(f"  ❌ FAIL: Expected fake food (cals=0, queued=False), got cals={cals}, queued={is_queued}")
        else:
            # result can be None if LLM returns {'error': 'unknown'}
            if not should_be_real:
                print("  ✅ PASS (returned None/Error)")
            else:
                print("  ❌ FAIL: Real food returned None")
        
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_llm_offline_behavior())
