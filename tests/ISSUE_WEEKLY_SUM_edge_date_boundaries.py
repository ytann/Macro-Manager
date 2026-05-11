import pytest
from app.services.database import DatabaseManager
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_weekly_summary_boundaries():
    db = DatabaseManager()
    
    # Exactly 7 days ago (should be included)
    date_7 = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    # 8 days ago (should be excluded)
    date_8 = (datetime.now() - timedelta(days=8)).strftime('%Y-%m-%d %H:%M:%S')
    
    with db.get_macros_conn() as conn:
        conn.execute("DELETE FROM meals")
        conn.execute("INSERT INTO meals (meal_id, timestamp, total_cals, items_json) VALUES (?, ?, ?, ?)", ('m1', date_7, 100, '[]'))
        conn.execute("INSERT INTO meals (meal_id, timestamp, total_cals, items_json) VALUES (?, ?, ?, ?)", ('m2', date_8, 200, '[]'))
        conn.commit()
        
    summary = db.get_weekly_summary()
    assert summary['calories'] == 100
    assert summary['days_logged'] == 1
