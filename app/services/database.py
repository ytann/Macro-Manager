import sqlite3
import json
import threading
from typing import Dict
from app.core.config import Config
from app.core import queries

DB_PATH = Config.FOODBANK_DB_PATH

DEFAULT_FOODS = [
    ('Rice', 'chawal', 130, 2.7, 28, 0.3, 0.4, 0, 0, 'initial_seed'),
    ('Lentils', 'dal daal pulses', 116, 9, 20, 1, 8, 0, 0, 'initial_seed'),
    ('Red Spinach', 'laal bhaji lal math amaranth leaves', 23, 3, 4, 0, 2, 0, 0, 'initial_seed'),
    ('Paneer', 'cottage cheese', 265, 14, 1.2, 20, 0, 1, 0, 'initial_seed'),
    ('Roti', 'chapati phulka flatbread', 297, 9, 46, 8, 9, 0, 0, 'initial_seed'),
    ('Bhetki', 'barramundi asian seabass', 108, 20, 0, 3, 0, 1, 0, 'initial_seed'),
    ('Chicken Breast', 'murgh', 165, 31, 0, 3.6, 0, 1, 0, 'initial_seed'),
    ('Apple', 'seb', 52, 0.3, 14, 0.2, 2.4, 0, 0, 'initial_seed'),
    ('Penne Pasta', 'pasta macaroni', 131, 5, 25, 0.6, 2.5, 0, 0, 'initial_seed'),
    ('Heavy Cream', 'cream', 340, 2, 3, 35, 0, 0, 0, 'initial_seed'),
    ('Parmesan Cheese', 'parmesan', 431, 38, 4, 29, 0, 1, 0, 'initial_seed'),
    ('Butter', 'makkhan', 717, 0.9, 0.1, 81, 0, 0, 0, 'initial_seed'),
]

def init_db():
    """Backward compatibility helper for tests."""
    db = DatabaseManager()
    return db

def save_meal(meal_data):
    """Backward compatibility helper for tests.
    meal_data is expected to be a dict as per old tests.
    """
    db = DatabaseManager()
    with db.get_macros_conn() as conn:
        # Adapt old meal format to new schema
        items = meal_data['items']
        total_p = sum(i['macros']['protein'] for i in items)
        total_c = sum(i['macros']['carbs'] for i in items)
        total_f = sum(i['macros']['fat'] for i in items)
        total_cal = sum(i['cals'] for i in items)
        
        def sum_sub(key):
            return sum((i.get('sub_macros') or {}).get(key, 0) or 0 for i in items)
            
        conn.execute(
            queries.MEALS_INSERT,
            (meal_data['meal_id'], json.dumps(items), total_p, total_c, total_f, total_cal, sum_sub('fiber'), sum_sub('sugar'), sum_sub('saturated_fat'), sum_sub('unsaturated_fat'), 'General')
        )
        conn.commit()

def get_todays_macros():
    """Backward compatibility helper for tests."""
    db = DatabaseManager()
    with db.get_macros_conn() as conn:
        cursor = conn.execute(queries.MEALS_GET_TODAY_BASIC)
        rows = cursor.fetchall()
        if not rows:
            return None
        
        totals = {
            "protein": sum(r[0] for r in rows),
            "carbs": sum(r[1] for r in rows),
            "fat": sum(r[2] for r in rows),
            "calories": sum(r[3] for r in rows),
        }
        return {"totals": totals}

class DatabaseManager:
    """
    Manager for SQLite operations.
    Handles both the foodbank (static/learned nutrition) and macro logs (daily meals).
    """
    def __init__(self):
        self._local = threading.local()
        self._init_db()

    def _init_db(self):
        self.foodbank_path = Config.FOODBANK_DB_PATH
        self.macros_path = Config.MACROS_DB_PATH
        self._init_foodbank()
        self._init_macros()

    def _init_foodbank(self):
        with sqlite3.connect(self.foodbank_path) as conn:
            cursor = conn.cursor()
            cursor.execute(queries.SCHEMA_FOODS_FTS)
            cursor.execute(queries.SCHEMA_RECIPES)
            cursor.execute(queries.SCHEMA_PENDING_VERIFICATION)
            # Migration: Add retry_count if missing
            cursor.execute(queries.SCHEMA_PENDING_VERIFICATION_INFO)
            cols = [row[1] for row in cursor.fetchall()]
            if 'retry_count' not in cols:
                cursor.execute(queries.SCHEMA_PENDING_VERIFICATION_ADD_RETRY)
            cursor.execute(queries.SCHEMA_SYNC_STATUS)
            
            # Initialize sync status if empty
            cursor.execute(queries.SCHEMA_SYNC_STATUS_COUNT)
            if cursor.fetchone()[0] == 0:
                cursor.execute(queries.SCHEMA_SYNC_STATUS_INIT)
            
            cursor.execute(queries.SCHEMA_FOODS_COUNT)
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.executemany(queries.FOODS_SEED_INSERT, DEFAULT_FOODS)
                conn.commit()

    def _init_macros(self):
        with sqlite3.connect(self.macros_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(queries.SCHEMA_MEALS)
            cursor.execute(queries.SCHEMA_GOALS)
            cursor = conn.execute(queries.SCHEMA_MEALS_INFO)
            columns = [row['name'] for row in cursor.fetchall()]
            required = {"total_fiber": "REAL", "total_sugar": "REAL", "total_saturated_fat": "REAL", "total_unsaturated_fat": "REAL", "meal_type": "TEXT"}
            for col, col_type in required.items():
                if col not in columns:
                    conn.execute(queries.SCHEMA_MEALS_ADD_COL.format(col=col, col_type=col_type))
            conn.commit()
 
    def get_foodbank_conn(self):
        if not hasattr(self._local, 'foodbank_conn'):
            conn = sqlite3.connect(self.foodbank_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local.foodbank_conn = conn
        return self._local.foodbank_conn

    def get_macros_conn(self):
        if not hasattr(self._local, 'macros_conn'):
            conn = sqlite3.connect(self.macros_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local.macros_conn = conn
        return self._local.macros_conn
 
    def set_daily_goals(self, protein: float, carbs: float, fat: float, calories: float):
        with self.get_macros_conn() as conn:
            conn.execute(
                queries.GOALS_UPSERT,
                (protein, carbs, fat, calories)
            )
            conn.commit()
 
    def get_daily_goals(self) -> Dict[str, float]:
        with self.get_macros_conn() as conn:
            row = conn.execute(queries.GOALS_GET).fetchone()
            if row:
                return {
                    "protein": row["protein"],
                    "carbs": row["carbs"],
                    "fat": row["fat"],
                    "calories": row["calories"]
                }
        return {"calories": 2000, "protein": 150, "carbs": 200, "fat": 65}

    def get_weekly_summary(self) -> dict:
        with self.get_macros_conn() as conn:
            cursor = conn.execute(
                queries.MEALS_WEEKLY_SUMMARY
            )
            row = cursor.fetchone()
            
            if not row or row['cal'] is None:
                # Handle the case where no meals are found or all are NULL
                # We still want the actual days_logged count if it exists
                days = row['days_logged'] if row else 0
                return {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'days_logged': days or 0}
            
            return {
                'calories': row['cal'] or 0,
                'protein': row['pro'] or 0,
                'carbs': row['car'] or 0,
                'fat': row['fat'] or 0,
                'days_logged': row['days_logged'] or 0
            }


