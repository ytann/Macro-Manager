import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_ddg_failure_resilience():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    # Mock the network to return 500
    with patch.object(fb.http_client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value.status_code = 500
        
        try:
            await fb.search_web_for_food("Apple")
            print("✅ PASS: Handled network failure without crashing.")
        except Exception as e:
            print(f"❌ FAIL: Crashed on network failure: {e}")

if __name__ == "__main__":
    asyncio.run(test_ddg_failure_resilience())
