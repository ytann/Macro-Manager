import pytest
from app.services.database import DatabaseManager

@pytest.mark.asyncio
async def test_weekly_summary_empty():
    db = DatabaseManager()
    # Ensure table is empty for this test
    with db.get_macros_conn() as conn:
        conn.execute("DELETE FROM meals")
        conn.commit()
    
    summary = db.get_weekly_summary()
    assert summary == {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'days_logged': 0}
