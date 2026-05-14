
import os
import sqlite3
import datetime
from app.services.database import DatabaseManager
from app.core import queries
from app.core.config import Config

def test_clear_data_logic():
    # 1. Setup: Clean DB and insert some data
    db_path = Config.MACROS_DB_PATH
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db_manager = DatabaseManager()
    
    # Insert some meals for today
    today = datetime.date.today().strftime('%Y-%m-%d %H:%M:%S')
    with db_manager.get_macros_conn() as conn:
        conn.execute(
            "INSERT INTO meals (meal_id, items_json, total_protein, total_carbs, total_fat, total_cals, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test_meal", "[]", 10.0, 10.0, 10.0, 100.0, today)
        )
        conn.commit()
    
    # Verify data is there
    with db_manager.get_macros_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM meals").fetchone()[0]
        print(f"Before clear: {count} meals")
        assert count > 0

    # 2. Execute clear logic (mimicking the API endpoint)
    try:
        with db_manager.get_macros_conn() as conn:
            conn.execute(queries.MEALS_DELETE_TODAY)
            conn.commit()
        print("Clear logic executed successfully")
    except Exception as e:
        print(f"Clear logic failed: {e}")
        raise e

    # 3. Verify data is gone
    with db_manager.get_macros_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM meals").fetchone()[0]
        print(f"After clear: {count} meals")
        assert count == 0

if __name__ == "__main__":
    test_clear_data_logic()
