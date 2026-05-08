import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_find_source_of_truth_request_count():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    # Mock the fetch_web_page method to count calls
    with patch.object(fb, '_fetch_web_page', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = "<html>Some nutrition data here...</html>"
        
        await fb.find_source_of_truth("Apple")
        
        print(f"Number of network fetches for find_source_of_truth: {mock_fetch.call_count}")
        if mock_fetch.call_count == 1:
            print("✅ PASS: Only one request made.")
        else:
            print(f"❌ FAIL: {mock_fetch.call_count} requests made. Expected 1.")

if __name__ == "__main__":
    asyncio.run(test_find_source_of_truth_request_count())
