import pytest
from app.services.database import DatabaseManager

@pytest.mark.asyncio
async def test_weekly_summary_nulls():
    db = DatabaseManager()
    
    with db.get_macros_conn() as conn:
        conn.execute("DELETE FROM meals")
        # Insert meal with NULL macros
        conn.execute(
            "INSERT INTO meals (meal_id, timestamp, total_protein, total_carbs, total_fat, total_cals, items_json) VALUES (?, 'now', NULL, NULL, NULL, NULL, ?)",
            ('null_meal', '[]')
        )
        conn.commit()
        
    summary = db.get_weekly_summary()
    assert summary['calories'] == 0
    assert summary['protein'] == 0
    assert summary['carbs'] == 0
    assert summary['fat'] == 0
    assert summary['days_logged'] == 1
