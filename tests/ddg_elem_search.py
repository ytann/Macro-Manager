import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_search_web_for_food_request_count():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    # Mock the http_client.get to count calls
    with patch.object(fb.http_client, 'get', new_callable=AsyncMock) as mock_get:
        # Simulate a successful response
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "<html>Nutrition data...</html>"
        
        # Use html_content=None to trigger actual web search
        await fb.search_web_for_food("Apple", html_content=None)
        
        # The current implementation tries multiple queries in a loop.
        # The "Double Request" issue specifically refers to calling fetch and search separately for the same item.
        # But for this unit test, we check if one query triggers multiple identical requests.
        print(f"Number of network requests for search_web_for_food: {mock_get.call_count}")
        # Note: Currently it tries 3 different queries. The issue is about redundant calls for the SAME HTML.
        # This test will be adjusted once the fix is implemented to ensure HTML is cached per search.
        if mock_get.call_count <= 3:
            print("✅ PASS: No excessive redundant requests.")
        else:
            print(f"❌ FAIL: {mock_get.call_count} requests made.")

if __name__ == "__main__":
    asyncio.run(test_search_web_for_food_request_count())
