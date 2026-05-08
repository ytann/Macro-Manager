import asyncio
import sys
import os
from unittest.mock import MagicMock, patch
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_fts5_redundant_delete():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    # Mock the database connection and cursor
    with patch.object(db, 'get_foodbank_conn') as mock_get_conn:
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        await fb.upsert_food("TestFood", 100, 1, 20, 1, 2, 0)
        
        # Check if "DELETE FROM foods" was called
        calls = [call[0][0] for call in mock_conn.execute.call_args_list]
        delete_calls = [c for c in calls if "DELETE FROM foods" in c]
        
        if len(delete_calls) > 0:
            print(f"❌ FAIL: Found {len(delete_calls)} redundant DELETE calls in upsert_food.")
        else:
            print("✅ PASS: No redundant DELETE calls found.")

if __name__ == "__main__":
    asyncio.run(test_fts5_redundant_delete())
