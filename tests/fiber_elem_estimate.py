import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_fiber_key_internal_estimate():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    with patch('litellm.acompletion', new_callable=AsyncMock) as mock_llm:
        # Simulate a response with 'fiber' key
        mock_llm.return_value.choices = [AsyncMock(message=AsyncMock(content='{"calories":100, "fiber":5, "is_real_food":true}'))]
        
        # We call get_nutrition_data while offline to trigger internal_estimate
        with patch.object(fb, '_is_network_available', return_value=False):
            result = await fb.get_nutrition_data("Apple")
            
            if result and 'fiber' in result:
                print("✅ PASS: 'fiber' is a top-level key in internal estimate result.")
            else:
                print(f"❌ FAIL: 'fiber' missing or nested in estimate result: {result}")

if __name__ == "__main__":
    asyncio.run(test_fiber_key_internal_estimate())
