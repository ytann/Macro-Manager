# SQL Queries
# Foodbank
FOODS_SEARCH_BY_NAME = "SELECT * FROM foods WHERE name = ? COLLATE NOCASE OR aliases LIKE ? COLLATE NOCASE LIMIT 1"
FOODS_SEARCH_MATCH = "SELECT * FROM foods WHERE foods MATCH ? ORDER BY rank LIMIT 1"
RECIPES_GET_BY_NAME = "SELECT recipe_json FROM recipes WHERE dish_name = ?"
RECIPES_UPSERT = "INSERT OR REPLACE INTO recipes (dish_name, recipe_json) VALUES (?, ?)"
FOODS_UPSERT = "INSERT OR REPLACE INTO foods (rowid, name, aliases, calories, protein, carbs, fat, fiber, sugar, saturated_fat, unsaturated_fat, is_complete_protein, verified, source) VALUES ((SELECT rowid FROM foods WHERE name = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
PENDING_VERIFICATION_UPSERT = "INSERT OR REPLACE INTO pending_verification (name, retry_count) VALUES (?, COALESCE((SELECT retry_count FROM pending_verification WHERE name = ?), 0))"
PENDING_VERIFICATION_GET_ALL = "SELECT name, retry_count FROM pending_verification"
PENDING_VERIFICATION_DELETE = "DELETE FROM pending_verification WHERE name = ?"
PENDING_VERIFICATION_INC_RETRY = "UPDATE pending_verification SET retry_count = retry_count + 1 WHERE name = ?"
PENDING_VERIFICATION_COUNT = "SELECT COUNT(*) FROM pending_verification"
SYNC_STATUS_UPDATE = "UPDATE sync_status SET last_sync = datetime('now') WHERE id = 1"
SYNC_STATUS_GET = "SELECT last_sync FROM sync_status WHERE id = 1"
FOODS_SEED_INSERT = "INSERT INTO foods (name, aliases, calories, protein, carbs, fat, fiber, sugar, saturated_fat, unsaturated_fat, is_complete_protein, verified, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

# Macros
MEALS_INSERT = "INSERT INTO meals (meal_id, items_json, total_protein, total_carbs, total_fat, total_cals, total_fiber, total_sugar, total_saturated_fat, total_unsaturated_fat, meal_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
MEALS_GET_TODAY_FULL = "SELECT total_protein, total_carbs, total_fat, total_cals, total_fiber, total_sugar, total_saturated_fat, total_unsaturated_fat, meal_type, items_json FROM meals WHERE date(timestamp) = date('now')"
MEALS_GET_TODAY_BASIC = "SELECT total_protein, total_carbs, total_fat, total_cals FROM meals WHERE date(timestamp) = date('now')"
MEALS_GET_TODAY_IDS = "SELECT id, meal_id, timestamp, items_json FROM meals WHERE date(timestamp) = date('now')"
MEALS_DELETE_TODAY = "DELETE FROM meals WHERE date(timestamp) = date('now')"
MEALS_WEEKLY_SUMMARY = "SELECT SUM(total_cals) as cal, SUM(total_protein) as pro, SUM(total_carbs) as car, SUM(total_fat) as fat, COUNT(DISTINCT date(timestamp)) as days_logged FROM meals WHERE date(timestamp) >= date('now', 'localtime', 'weekday 0', '-6 days')"
GOALS_UPSERT = "INSERT OR REPLACE INTO goals (id, protein, carbs, fat, calories) VALUES (1, ?, ?, ?, ?)"
GOALS_GET = "SELECT protein, carbs, fat, calories FROM goals WHERE id = 1"

# Schema Initialization
SCHEMA_FOODS_FTS = """
    CREATE VIRTUAL TABLE IF NOT EXISTS foods USING fts5(
        name, aliases, calories UNINDEXED, protein UNINDEXED, 
        carbs UNINDEXED, fat UNINDEXED, fiber UNINDEXED, 
        sugar UNINDEXED, saturated_fat UNINDEXED, unsaturated_fat UNINDEXED,
        is_complete_protein UNINDEXED,
        verified UNINDEXED, source UNINDEXED
    )
"""
SCHEMA_RECIPES = "CREATE TABLE IF NOT EXISTS recipes (dish_name TEXT PRIMARY KEY, recipe_json TEXT NOT NULL)"
SCHEMA_PENDING_VERIFICATION = "CREATE TABLE IF NOT EXISTS pending_verification (name TEXT PRIMARY KEY, retry_count INTEGER DEFAULT 0)"
SCHEMA_PENDING_VERIFICATION_INFO = "PRAGMA table_info(pending_verification)"
SCHEMA_PENDING_VERIFICATION_ADD_RETRY = "ALTER TABLE pending_verification ADD COLUMN retry_count INTEGER DEFAULT 0"
SCHEMA_SYNC_STATUS = "CREATE TABLE IF NOT EXISTS sync_status (id INTEGER PRIMARY KEY, last_sync DATETIME)"
SCHEMA_SYNC_STATUS_COUNT = "SELECT COUNT(*) FROM sync_status"
SCHEMA_SYNC_STATUS_INIT = "INSERT INTO sync_status (id, last_sync) VALUES (1, '1970-01-01 00:00:00')"
SCHEMA_FOODS_COUNT = "SELECT COUNT(*) FROM foods"
SCHEMA_MEALS = """
    CREATE TABLE IF NOT EXISTS meals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_id TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        items_json TEXT NOT NULL,
        total_protein REAL, total_carbs REAL, total_fat REAL, total_cals REAL,
        total_fiber REAL, total_sugar REAL, total_saturated_fat REAL, total_unsaturated_fat REAL,
        meal_type TEXT
    )
"""
SCHEMA_GOALS = """
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY,
        protein REAL,
        carbs REAL,
        fat REAL,
        calories REAL
    )
"""
SCHEMA_MEALS_INFO = "PRAGMA table_info(meals)"
SCHEMA_MEALS_ADD_COL = "ALTER TABLE meals ADD COLUMN {col} {col_type}"

# External Query Templates
DDG_SEARCH_URL = "https://html.duckduckgo.com/html/?q={query}"
NUTRITION_FACTS_QUERY = "nutrition facts {name} per 100g calories protein carbs fat fiber"
WEB_SEARCH_QUERIES = [
    "{dish_name} nutrition facts per 100g",
    "average calories protein carbs fat for {dish_name}",
    "{dish_name} recipe ingredients weights"
]
