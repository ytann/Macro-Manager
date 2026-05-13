import pytest
import sqlite3
import asyncio
from unittest.mock import MagicMock, patch
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

@pytest.mark.asyncio
async def test_seeding_works():
    db_path = "test_seed.db"
    mock_db = MagicMock()
    mock_db.foodbank_path = db_path
    mock_db.get_foodbank_conn = lambda: sqlite3.connect(db_path)
    
    # Create table first
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS foods USING fts5(name, aliases, calories UNINDEXED, protein UNINDEXED, carbs UNINDEXED, fat UNINDEXED, fiber UNINDEXED, is_complete_protein UNINDEXED, verified UNINDEXED, source UNINDEXED)")
    conn.commit()
    conn.close()
    
    with patch.object(FoodbankService, '_load_prompts', return_value={}):
        service = FoodbankService(mock_db)
    
    # Initial seed via DatabaseManager (implicitly called in __init__ if we used real DBManager)
    # But since we used mock_db, we call seed_db explicitly
    await service.seed_db()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM foods")
    count = cursor.fetchone()[0]
    conn.close()
    
    assert count == 12, f"Expected 12 seeded foods, got {count}"

if __name__ == "__main__":
    asyncio.run(test_seeding_works())

