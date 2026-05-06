import sqlite3
import json
from typing import Any

DB_PATH = "macros.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                items_json TEXT NOT NULL,
                total_protein REAL,
                total_carbs REAL,
                total_fat REAL,
                total_cals REAL,
                total_fiber REAL,
                total_sugar REAL,
                total_saturated_fat REAL,
                total_unsaturated_fat REAL,
                meal_type TEXT
            )
        """)
        
        # Schema Migration: Ensure all columns exist
        cursor = conn.execute("PRAGMA table_info(meals)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        required_columns = {
            "total_fiber": "REAL",
            "total_sugar": "REAL",
            "total_saturated_fat": "REAL",
            "total_unsaturated_fat": "REAL",
            "meal_type": "TEXT"
        }
        
        for col, col_type in required_columns.items():
            if col not in columns:
                conn.execute(f"ALTER TABLE meals ADD COLUMN {col} {col_type}")
        
        conn.commit()

def save_meal(meal_data: Any, meal_type: str = "General"):
    """
    Saves a FoodLog object to the database.
    Calculates totals before saving.
    """
    # Handle both Pydantic model and dict
    data = meal_data if isinstance(meal_data, dict) else meal_data.model_dump()
    
    total_protein = sum(item['macros']['protein'] for item in data['items'])
    total_carbs = sum(item['macros']['carbs'] for item in data['items'])
    total_fat = sum(item['macros']['fat'] for item in data['items'])
    total_cals = sum(item['cals'] for item in data['items'])
    
    # Helper to sum sub-macros safely
    def sum_sub(key):
        return sum((item.get('sub_macros') or {}).get(key, 0) or 0 for item in data['items'])
        
    total_fiber = sum_sub('fiber')
    total_sugar = sum_sub('sugar')
    total_saturated_fat = sum_sub('saturated_fat')
    total_unsaturated_fat = sum_sub('unsaturated_fat')
    
    with get_db() as conn:
        conn.execute(
            "INSERT INTO meals (meal_id, items_json, total_protein, total_carbs, total_fat, total_cals, total_fiber, total_sugar, total_saturated_fat, total_unsaturated_fat, meal_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (data['meal_id'], json.dumps(data['items']), total_protein, total_carbs, total_fat, total_cals, total_fiber, total_sugar, total_saturated_fat, total_unsaturated_fat, meal_type)
        )
        conn.commit()
    print(f"DB: Saved meal {data['meal_id']} with {len(data['items'])} items.")


def get_todays_macros():
    """
    Retrieves totals for all meals logged today and groups them by meal type.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT total_protein, total_carbs, total_fat, total_cals, total_fiber, total_sugar, total_saturated_fat, total_unsaturated_fat, meal_type, items_json FROM meals WHERE date(timestamp) = date('now')"
        )
        rows = cursor.fetchall()
        
        totals = {
            "protein": sum(row['total_protein'] for row in rows),
            "carbs": sum(row['total_carbs'] for row in rows),
            "fat": sum(row['total_fat'] for row in rows),
            "calories": sum(row['total_cals'] for row in rows),
            "fiber": sum(row['total_fiber'] for row in rows),
            "sugar": sum(row['total_sugar'] for row in rows),
            "saturated_fat": sum(row['total_saturated_fat'] for row in rows),
            "unsaturated_fat": sum(row['total_unsaturated_fat'] for row in rows)
        }
        
        grouped_meals = {}
        for row in rows:
            m_type = row['meal_type'] or "General"
            if m_type not in grouped_meals:
                grouped_meals[m_type] = []
            grouped_meals[m_type].append(json.loads(row['items_json']))
            
        return {
            "totals": totals,
            "grouped": grouped_meals
        }

def get_todays_meals():
    """
    Retrieves all meals logged today.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT id, meal_id, timestamp, items_json FROM meals WHERE date(timestamp) = date('now')"
        )
        rows = cursor.fetchall()
        
        meals = []
        for row in rows:
            meals.append({
                "id": row["id"],
                "meal_id": row["meal_id"],
                "timestamp": row["timestamp"],
                "items": json.loads(row["items_json"])
            })
        return meals

def clear_todays_meals():
    """
    Deletes all meals logged today.
    """
    with get_db() as conn:
        conn.execute("DELETE FROM meals WHERE date(timestamp) = date('now')")
        conn.commit()
        return True

def get_daily_goals():
    """
    Returns static daily nutrition goals.
    """
    return {
        "calories": 2000,
        "protein": 150,
        "carbs": 200,
        "fat": 65
    }

if __name__ == "__main__":
    init_db()
    print("DB initialized.")
