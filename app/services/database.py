import sqlite3
import json
import threading
from contextlib import contextmanager
from typing import Dict, Generator
from app.core.config import Config
from app.core import queries
from app.core.logger import logger


DB_PATH = Config.FOODBANK_DB_PATH

DEFAULT_FOODS = [
    # name, aliases, calories, protein, carbs, fat, fiber, sugar, sat_fat, unsat_fat, is_complete_protein, verified, source, category
    ('Rice', 'chawal', 130, 2.7, 28, 0.3, 0.4, 0, 0, 0, 0, 0, 'initial_seed', 'Starch/Breads'),
    ('Lentils', 'dal daal pulses', 116, 9, 20, 1, 8, 0, 0, 0, 0, 0, 'initial_seed', 'Starch/Breads'),
    ('Red Spinach', 'laal bhaji lal math amaranth leaves', 23, 3, 4, 0, 2, 0, 0, 0, 0, 0, 'initial_seed', 'Green Veggies'),
    ('Paneer', 'cottage cheese', 265, 14, 1.2, 20, 0, 1, 0, 0, 0, 0, 'initial_seed', 'Dairy/Paneer'),
    ('Roti', 'chapati phulka flatbread', 297, 9, 46, 8, 9, 0, 0, 0, 0, 0, 'initial_seed', 'Starch/Breads'),
    ('Bhetki', 'barramundi asian seabass', 108, 20, 0, 3, 0, 1, 0, 0, 0, 0, 'initial_seed', 'Seafood'),
    ('Chicken Breast', 'murgh', 165, 31, 0, 3.6, 0, 1, 0, 0, 0, 0, 'initial_seed', 'Poultry'),
    ('Apple', 'seb', 52, 0.3, 14, 0.2, 2.4, 0, 0, 0, 0, 0, 'initial_seed', 'Other/Misc'),
    ('Penne Pasta', 'pasta macaroni', 131, 5, 25, 0.6, 2.5, 0, 0, 0, 0, 0, 'initial_seed', 'Starch/Breads'),
    ('Heavy Cream', 'cream', 340, 2, 3, 35, 0, 0, 0, 0, 0, 0, 'initial_seed', 'Dairy/Paneer'),
    ('Parmesan Cheese', 'parmesan', 431, 38, 4, 29, 0, 1, 0, 0, 0, 0, 'initial_seed', 'Dairy/Paneer'),
    ('Butter', 'makkhan', 717, 0.9, 0.1, 81, 0, 0, 0, 0, 0, 0, 'initial_seed', 'Dairy/Paneer'),
    ('Mutton', 'gosht', 294, 25, 0, 21, 0, 0, 9, 12, 1, 1, 'initial_seed', 'Red Meat'),
    ('Egg', 'anda', 155, 13, 1.1, 11, 0, 1.1, 3.3, 4.2, 1, 1, 'initial_seed', 'Egg'),
    ('Soya Chunks', 'soya', 345, 52, 33, 0.5, 13, 0, 0.1, 0.2, 1, 1, 'initial_seed', 'Soya/Tofu'),
    ('Bacon', 'pork', 541, 37, 1.4, 42, 0, 0, 15, 19, 0, 1, 'initial_seed', 'Pork'),
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

            # Migration: Add 'category' column
            cursor.execute(queries.SCHEMA_FOODS_INFO)
            cols = [row[1] for row in cursor.fetchall()]
            if 'category' not in cols:
                # This will fail on FTS5, but we handle this by recreating in prod.
                # For local dev, it's fine.
                try:
                    cursor.execute(queries.SCHEMA_FOODS_ADD_CATEGORY)
                except sqlite3.OperationalError as e:
                    logger.warning(f"Could not add category column (likely FTS5 limitation): {e}")

            # Migration: Sprint 8 - Add per 100g columns
            cursor.execute(queries.SCHEMA_FOODS_INFO)
            cols = [row[1] for row in cursor.fetchall()]
            if 'reported_qty' not in cols:
                cursor.execute(queries.SCHEMA_FOODS_ADD_REPORTED_QTY)
                cursor.execute(queries.SCHEMA_FOODS_ADD_REPORTED_P)
                cursor.execute(queries.SCHEMA_FOODS_ADD_REPORTED_C)
                cursor.execute(queries.SCHEMA_FOODS_ADD_REPORTED_F)
                cursor.execute(queries.SCHEMA_FOODS_ADD_P_PER_100)
                cursor.execute(queries.SCHEMA_FOODS_ADD_C_PER_100)
                cursor.execute(queries.SCHEMA_FOODS_ADD_F_PER_100)
                # Since FTS5 tables don't support simple ALTER TABLE for adding columns easily,
                # the actual add column queries won't work on FTS5 without recreate.
                # However, this _init_foodbank only runs on empty DBs or tests, so it's fine.
                conn.commit()
            
            cursor.execute(queries.SCHEMA_FOODS_COUNT)
            count = cursor.fetchone()[0]
            if count == 0:
                # Seed with normalized data
                normalized_foods = self._normalize_default_foods()
                cursor.executemany(queries.FOODS_SEED_INSERT, normalized_foods)
                conn.commit()
    
    def _normalize_default_foods(self):
        """Normalize DEFAULT_FOODS to include per 100g values."""
        normalized = []
        for food in DEFAULT_FOODS:
            # Unpack the extended tuple with category
            name, aliases, calories, protein, carbs, fat, fiber, sugar, sat_fat, unsat_fat, is_complete, verified, source, category = food
            reported_qty = 100.0  # Assume all are per 100g
            p_per_100 = protein
            c_per_100 = carbs
            f_per_100 = fat
            reported_cal = calories
            cal_per_100 = calories
            reported_fiber = fiber
            fiber_per_100 = fiber
            # Extended tuple with new columns for the query
            normalized.append((name, aliases, calories, protein, carbs, fat, fiber, sugar, sat_fat, unsat_fat, is_complete, verified, source, category, reported_qty, protein, carbs, fat, p_per_100, c_per_100, f_per_100, reported_cal, cal_per_100, reported_fiber, fiber_per_100))
        return normalized


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

    @contextmanager
    def transaction(self, db_type='macros') -> Generator[sqlite3.Connection, None, None]:
        """Provides a transactional context for DB operations."""
        conn = self.get_macros_conn() if db_type == 'macros' else self.get_foodbank_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def run_foodbank(self, query, params=(), fetchone=False, fetchall=False, commit=False):
        """Helper to execute a query on the foodbank DB."""
        conn = self.get_foodbank_conn()
        cursor = conn.execute(query, params)
        if commit:
            conn.commit()
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()
        return cursor

    def run_foodbank_batch(self, query, params_list, commit=True):
        """Execute a query for multiple parameter sets using executemany."""
        conn = self.get_foodbank_conn()
        cursor = conn.executemany(query, params_list)
        if commit:
            conn.commit()
        return cursor

    def run_macros(self, query, params=(), fetchone=False, fetchall=False, commit=False):
        """Helper to execute a query on the macros DB."""
        conn = self.get_macros_conn()
        cursor = conn.execute(query, params)
        if commit:
            conn.commit()
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()
        return cursor
 
    def set_daily_goals(self, protein: float, carbs: float, fat: float, calories: float):
        with self.get_macros_conn() as conn:
            conn.execute(
                queries.GOALS_UPSERT,
                (protein, carbs, fat, calories)
            )
            conn.commit()
 
    def get_daily_goals(self) -> tuple[Dict[str, float], bool]:
        with self.get_macros_conn() as conn:
            row = conn.execute(queries.GOALS_GET).fetchone()
            if row:
                return {
                    "protein": row["protein"],
                    "carbs": row["carbs"],
                    "fat": row["fat"],
                    "calories": row["calories"]
                }, True
        return {"calories": 2000, "protein": 150, "carbs": 200, "fat": 65}, False

    def get_weekly_summary(self) -> dict:
        with self.get_macros_conn() as conn:
            cursor = conn.execute(
                queries.MEALS_WEEKLY_SUMMARY
            )
            row = cursor.fetchone()
            
            days_logged = row['days_logged'] if row else 0
            
            goals, _ = self.get_daily_goals()
            # Weekly goals are always based on a 7-day window for the progress bars
            weekly_goals = {
                'calories': goals['calories'] * 7,
                'protein': goals['protein'] * 7,
                'carbs': goals['carbs'] * 7,
                'fat': goals['fat'] * 7,
            }

 
            if not row or row['cal'] is None:
                return {
                    'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 
                    'days_logged': days_logged, 'weekly_goals': weekly_goals
                }
            
            return {
                'calories': row['cal'] or 0,
                'protein': row['pro'] or 0,
                'carbs': row['car'] or 0,
                'fat': row['fat'] or 0,
                'days_logged': days_logged,
                'weekly_goals': weekly_goals
            }



