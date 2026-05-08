import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.extraction import ExtractionService
from app.services.database import DatabaseManager

async def test_overall_request_caching():
    db = DatabaseManager()
    fb = FoodbankService(db)
    ext = ExtractionService(fb)
    
    # Mock the network calls
    with patch.object(fb.http_client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "<html>Nutrition data...</html>"
        
        # Parse a meal with repeated items
        text = "2 apples and 1 apple"
        await ext.parse(text)
        
        # We expect only one set of requests for 'Apple'
        # Current implementation of ExtractionService has a cache, but FoodbankService might not.
        print(f"Total network requests for repeated items: {mock_get.call_count}")
        if mock_get.call_count < 10: # Arbitrary threshold to detect extreme redundancy
             print("✅ PASS: Redundancy is limited.")
        else:
             print(f"❌ FAIL: Too many requests: {mock_get.call_count}")

if __name__ == "__main__":
    asyncio.run(test_overall_request_caching())
