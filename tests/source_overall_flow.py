import asyncio
import sys
import os
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_source_flow():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    test_food = "SourceFlowFood"
    
    # 1. Trigger Source of Truth search
    # We mock the network to provide specific HTML
    with patch('app.services.foodbank.FoodbankService._fetch_web_page', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = "<html>Source: https://example.com/nutrition</html>"
        
        await fb.find_source_of_truth(test_food)
        
        # 2. Verify in DB
        conn = db.get_foodbank_conn()
        row = conn.execute("SELECT source FROM foods WHERE name = ?", (test_food,)).fetchone()
        conn.close()
        
        if row and row['source']:
            print(f"✅ PASS: Source persisted correctly: {row['source']}")
        else:
            print("❌ FAIL: Source not found in DB after SoT search.")

if __name__ == "__main__":
    # Patch needs to be inside the script if not using a test runner
    from unittest.mock import AsyncMock, patch
    asyncio.run(test_source_flow())
