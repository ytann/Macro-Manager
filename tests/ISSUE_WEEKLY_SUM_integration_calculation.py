import pytest
from app.services.database import DatabaseManager
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_weekly_summary_calculation():
    db = DatabaseManager()
    
    # Data setup
    now = datetime.now()
    day_0 = now.strftime('%Y-%m-%d %H:%M:%S')
    day_3 = (now - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
    day_8 = (now - timedelta(days=8)).strftime('%Y-%m-%d %H:%M:%S')
    
    test_meals = [
        # Day 0: 2 meals
        (day_0, 500, 20, 50, 10),
        (day_0, 300, 10, 30, 5),
        # Day 3: 1 meal
        (day_3, 400, 15, 40, 8),
        # Day 8: 1 meal (Should be excluded)
        (day_8, 1000, 50, 100, 20),
    ]
    
    with db.get_macros_conn() as conn:
        conn.execute("DELETE FROM meals")
        for ts, cal, pro, car, fat in test_meals:
            conn.execute(
                "INSERT INTO meals (meal_id, timestamp, total_protein, total_carbs, total_fat, total_cals, items_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ('test_id', ts, pro, car, fat, cal, '[]')
            )
        conn.commit()
    
    summary = db.get_weekly_summary()
    
    # Expected: 500+300+400 = 1200 cal, 20+10+15 = 45 pro, etc.
    assert summary['calories'] == 1200
    assert summary['protein'] == 45
    assert summary['carbs'] == 120
    assert summary['fat'] == 23
    assert summary['days_logged'] == 2
