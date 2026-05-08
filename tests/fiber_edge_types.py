import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_fiber_type_handling():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    # Test a response where fiber is a string instead of float
    with patch('litellm.acompletion', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value.choices = [AsyncMock(message=AsyncMock(content='{"calories":100, "fiber":"5.5", "is_real_food":true}'))]
        
        with patch.object(fb, '_is_network_available', return_value=False):
            try:
                result = await fb.get_nutrition_data("Apple")
                if result and isinstance(result.get('fiber'), float):
                    print("✅ PASS: Normalized fiber string to float.")
                else:
                    print(f"❌ FAIL: Fiber not normalized to float: {result.get('fiber')}")
            except Exception as e:
                print(f"❌ FAIL: Crashed on string fiber: {e}")

if __name__ == "__main__":
    asyncio.run(test_fiber_type_handling())
