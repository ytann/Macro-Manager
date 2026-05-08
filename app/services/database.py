import sqlite3
import json
from typing import Dict
from app.core.config import Config

DB_PATH = Config.FOODBANK_DB_PATH

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
            "INSERT INTO meals (meal_id, items_json, total_protein, total_carbs, total_fat, total_cals, total_fiber, total_sugar, total_saturated_fat, total_unsaturated_fat, meal_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (meal_data['meal_id'], json.dumps(items), total_p, total_c, total_f, total_cal, sum_sub('fiber'), sum_sub('sugar'), sum_sub('saturated_fat'), sum_sub('unsaturated_fat'), 'General')
        )
        conn.commit()

def get_todays_macros():
    """Backward compatibility helper for tests."""
    db = DatabaseManager()
    with db.get_macros_conn() as conn:
        cursor = conn.execute("SELECT total_protein, total_carbs, total_fat, total_cals FROM meals WHERE date(timestamp) = date('now')")
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
        self._init_db()

    def _init_db(self):
        self.foodbank_path = Config.FOODBANK_DB_PATH
        self.macros_path = Config.MACROS_DB_PATH
        self._init_foodbank()
        self._init_macros()

    def _init_foodbank(self):
        with sqlite3.connect(self.foodbank_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS foods")
            cursor.execute("""
                CREATE VIRTUAL TABLE foods USING fts5(
                    name, aliases, calories UNINDEXED, protein UNINDEXED, 
                    carbs UNINDEXED, fat UNINDEXED, fiber UNINDEXED, is_complete_protein UNINDEXED,
                    verified UNINDEXED, source UNINDEXED
                )
            """)
            cursor.execute("CREATE TABLE IF NOT EXISTS recipes (dish_name TEXT PRIMARY KEY, recipe_json TEXT NOT NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS pending_verification (name TEXT PRIMARY KEY, retry_count INTEGER DEFAULT 0)")
            # Migration: Add retry_count if missing
            cursor.execute("PRAGMA table_info(pending_verification)")
            cols = [row[1] for row in cursor.fetchall()]
            if 'retry_count' not in cols:
                cursor.execute("ALTER TABLE pending_verification ADD COLUMN retry_count INTEGER DEFAULT 0")
            cursor.execute("CREATE TABLE IF NOT EXISTS sync_status (id INTEGER PRIMARY KEY, last_sync DATETIME)")
            
            # Initialize sync status if empty
            cursor.execute("SELECT COUNT(*) FROM sync_status")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO sync_status (id, last_sync) VALUES (1, '1970-01-01 00:00:00')")
            
            cursor.execute("SELECT COUNT(*) FROM foods")
            count = cursor.fetchone()[0]
            if count == 0:
                foods = [
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
                cursor.executemany("INSERT INTO foods VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", foods)
                conn.commit()

    def _init_macros(self):
        with sqlite3.connect(self.macros_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meal_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    items_json TEXT NOT NULL,
                    total_protein REAL, total_carbs REAL, total_fat REAL, total_cals REAL,
                    total_fiber REAL, total_sugar REAL, total_saturated_fat REAL, total_unsaturated_fat REAL,
                    meal_type TEXT
                )
            """)
            cursor = conn.execute("PRAGMA table_info(meals)")
            columns = [row['name'] for row in cursor.fetchall()]
            required = {"total_fiber": "REAL", "total_sugar": "REAL", "total_saturated_fat": "REAL", "total_unsaturated_fat": "REAL", "meal_type": "TEXT"}
            for col, col_type in required.items():
                if col not in columns:
                    conn.execute(f"ALTER TABLE meals ADD COLUMN {col} {col_type}")
            conn.commit()

    def get_foodbank_conn(self):
        conn = sqlite3.connect(self.foodbank_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def get_macros_conn(self):
        conn = sqlite3.connect(self.macros_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def get_daily_goals(self) -> Dict[str, float]:
        return {"calories": 2000, "protein": 150, "carbs": 200, "fat": 65}

