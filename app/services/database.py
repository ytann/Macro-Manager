import sqlite3
import json
from typing import Any, Optional, List, Dict
from app.core.config import Config

class DatabaseManager:
    """
    Singleton Manager for SQLite operations.
    Handles both the foodbank (static/learned nutrition) and macro logs (daily meals).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

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
                    verified UNINDEXED
                )
            """)
            cursor.execute("CREATE TABLE IF NOT EXISTS recipes (dish_name TEXT PRIMARY KEY, recipe_json TEXT NOT NULL)")
            
            foods = [
                ('Rice', 'chawal', 130, 2.7, 28, 0.3, 0.4, 0, 0),
                ('Lentils', 'dal daal pulses', 116, 9, 20, 1, 8, 0, 0),
                ('Red Spinach', 'laal bhaji lal math amaranth leaves', 23, 3, 4, 0, 2, 0, 0),
                ('Paneer', 'cottage cheese', 265, 14, 1.2, 20, 0, 1, 0),
                ('Roti', 'chapati phulka flatbread', 297, 9, 46, 8, 9, 0, 0),
                ('Bhetki', 'barramundi asian seabass', 108, 20, 0, 3, 0, 1, 0),
                ('Chicken Breast', 'murgh', 165, 31, 0, 3.6, 0, 1, 0),
                ('Apple', 'seb', 52, 0.3, 14, 0.2, 2.4, 0, 0),
                ('Penne Pasta', 'pasta macaroni', 131, 5, 25, 0.6, 2.5, 0, 0),
                ('Heavy Cream', 'cream', 340, 2, 3, 35, 0, 0, 0),
                ('Parmesan Cheese', 'parmesan', 431, 38, 4, 29, 0, 1, 0),
                ('Butter', 'makkhan', 717, 0.9, 0.1, 81, 0, 0, 0),
            ]
            cursor.executemany("INSERT INTO foods VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", foods)
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
        conn = sqlite3.connect(self.foodbank_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_macros_conn(self):
        conn = sqlite3.connect(self.macros_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_daily_goals(self) -> Dict[str, float]:
        return {"calories": 2000, "protein": 150, "carbs": 200, "fat": 65}

