import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_fiber_uniformity():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    # We want to ensure all paths return {'fiber': float}
    results = []
    
    with patch('litellm.acompletion', new_callable=AsyncMock) as mock_llm:
        # 1. Mock for SoT
        mock_llm.return_value.choices = [AsyncMock(message=AsyncMock(content='{"calories":100, "fiber":5, "confidence":"High"}'))]
        results.append(await fb.find_source_of_truth("Apple", html_content="<html></html>"))
        
        # 2. Mock for Web Search
        mock_llm.return_value.choices = [AsyncMock(message=AsyncMock(content='{"type":"ingredient", "calories":100, "fiber":6}'))]
        results.append(await fb.search_web_for_food("Apple"))
        
        # 3. Mock for Internal Estimate
        mock_llm.return_value.choices = [AsyncMock(message=AsyncMock(content='{"calories":100, "fiber":7, "is_real_food":true}'))]
        with patch.object(fb, '_is_network_available', return_value=False):
            results.append(await fb.get_nutrition_data("Apple"))
            
    # Verify all have 'fiber' at the same level and it's numeric
    all_uniform = True
    for i, res in enumerate(results):
        if not res or 'fiber' not in res or not isinstance(res['fiber'], (int, float)):
            print(f"❌ FAIL: Path {i} is not uniform: {res}")
            all_uniform = False
            
    if all_uniform:
        print("✅ PASS: All resolution paths return uniform fiber keys.")

if __name__ == "__main__":
    asyncio.run(test_fiber_uniformity())
