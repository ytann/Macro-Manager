import pytest
import sqlite3
import asyncio
from unittest.mock import MagicMock, patch
from app.services.foodbank import FoodbankService

@pytest.mark.asyncio
async def test_upsert_food_preserves_complete_protein():
    # Setup in-memory DB for testing
    # Use a file-based DB or handle connection per thread
    db_path = "test_upsert.db"
    
    # Create table
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS foods USING fts5(name, aliases, calories, protein, carbs, fat, fiber, is_complete_protein, verified, source)")
    conn.commit()
    conn.close()
    
    mock_db = MagicMock()
    mock_db.foodbank_path = db_path
    # Mimic DatabaseManager.get_foodbank_conn()
    mock_db.get_foodbank_conn = lambda: sqlite3.connect(db_path)
    
    with patch.object(FoodbankService, '_load_prompts', return_value={}):
        service = FoodbankService(mock_db)

    # Act: Upsert a food as a complete protein
    try:
        await service.upsert_food("Chicken", 165, 31, 0, 3.6, 0, verified=1, is_complete_protein=1)
    except TypeError as e:
        pytest.fail(f"upsert_food does not accept is_complete_protein: {e}")

    # Verify
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT is_complete_protein FROM foods WHERE name = 'Chicken'")
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None, "Food was not upserted"
    assert row[0] == 1, f"Expected is_complete_protein=1, got {row[0]}"

if __name__ == "__main__":
    asyncio.run(test_upsert_food_preserves_complete_protein())
