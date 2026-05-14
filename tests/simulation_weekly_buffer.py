
import os
import datetime
from app.services.database import DatabaseManager
from app.core.config import Config

def test_weekly_buffer_simulation():
    # 1. Setup: Clean DB
    db_path = Config.MACROS_DB_PATH
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = DatabaseManager()
    
    # Set goals
    daily_protein = 150.0
    daily_carbs = 200.0
    daily_fat = 65.0
    daily_cals = 2000.0
    db.set_daily_goals(daily_protein, daily_carbs, daily_fat, daily_cals)
    
    # 2. Simulation: 10 days of meals
    # Today is Thu May 14 2026.
    # Calendar Week: Mon May 11 to Sun May 17.
    
    today = datetime.date.today()
    
    # We want to test that only this week is counted.
    # Let's insert data for the last 10 days.
    
    test_days = []
    for i in range(10):
        day = today - datetime.timedelta(days=i)
        # Mix of under and over goals
        # Day 0 (Today): Over
        # Day 1 (Wed): Under
        # Day 2 (Tue): Under
        # Day 3 (Mon): Over
        # Day 4 (Sun - Prev Week): Under
        # Day 5 (Sat - Prev Week): Under
        # ...
        
        if i % 2 == 0: # Over
            p, c, f, cal = daily_protein * 1.2, daily_carbs * 1.2, daily_fat * 1.2, daily_cals * 1.2
        else: # Under
            p, c, f, cal = daily_protein * 0.8, daily_carbs * 0.8, daily_fat * 0.8, daily_cals * 0.8
            
        test_days.append((day, p, c, f, cal))

    # Insert into DB
    with db.get_macros_conn() as conn:
        for day, p, c, f, cal in test_days:
            timestamp = day.strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                "INSERT INTO meals (meal_id, items_json, total_protein, total_carbs, total_fat, total_cals, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"meal_{day}", "[]", p, c, f, cal, timestamp)
            )
        conn.commit()

    # 3. Verification
    summary = db.get_weekly_summary()
    
    print(f"\nSummary: {summary}")
    
    # Determine start of current calendar week (Monday)
    # For May 14 2026 (Thu), Monday is May 11.
    # test_days[0] = May 14 (Thu)
    # test_days[1] = May 13 (Wed)
    # test_days[2] = May 12 (Tue)
    # test_days[3] = May 11 (Mon)
    # test_days[4] = May 10 (Sun) -> Should be excluded
    
    expected_days_logged = 4 # Mon, Tue, Wed, Thu
    
    # Calculate expected totals for these 4 days
    expected_cal = 0
    expected_carbs = 0
    expected_fat = 0
    for i in range(4):
        day, p, c, f, cal = test_days[i]
        expected_cal += cal
        expected_carbs += c
        expected_fat += f
        
    print(f"Expected Days: {expected_days_logged}, Actual: {summary['days_logged']}")
    print(f"Expected Cal: {expected_cal}, Actual: {summary['calories']}")
    print(f"Expected Carbs: {expected_carbs}, Actual: {summary['carbs']}")
    
    assert summary['days_logged'] == expected_days_logged, f"Days logged mismatch: {summary['days_logged']} vs {expected_days_logged}"
    assert abs(summary['calories'] - expected_cal) < 1.0, f"Calories mismatch: {summary['calories']} vs {expected_cal}"
    assert abs(summary['carbs'] - expected_carbs) < 1.0, f"Carbs mismatch: {summary['carbs']} vs {expected_carbs}"

    # 4. Simulation of Frontend Cheat Bank logic
    # accumulated_savings = max(0, (daily_goal * days_active) - total_consumed_this_week)
    days_active = summary['days_logged']
    daily_carb_goal = daily_carbs
    
    # Test case: Total consumed is more than the weekly goal (should be 0)
    # Let's force a scenario where we overate a lot
    with db.get_macros_conn() as conn:
        conn.execute("UPDATE meals SET total_carbs = 1000 WHERE date(timestamp) = date('now')")
        conn.commit()
    
    summary_over = db.get_weekly_summary()
    total_consumed_carbs = summary_over['carbs']
    
    savings = (daily_carb_goal * days_active) - total_consumed_carbs
    actual_savings = max(0, savings)
    
    print(f"Raw Savings: {savings}, Capped Savings: {actual_savings}")
    assert actual_savings == 0, "Savings should be capped at 0"

if __name__ == "__main__":
    test_weekly_buffer_simulation()
