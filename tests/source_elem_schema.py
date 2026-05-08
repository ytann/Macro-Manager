import sys
import os
import sqlite3
sys.path.append(os.getcwd())
from app.services.database import DatabaseManager

def test_source_column_exists():
    db = DatabaseManager()
    conn = db.get_foodbank_conn()
    cursor = conn.cursor()
    
    # FTS5 tables are a bit different. We check the table info or try a query.
    try:
        cursor.execute("SELECT source FROM foods LIMIT 1")
        print("✅ PASS: 'source' column exists in foods table.")
    except sqlite3.OperationalError as e:
        print(f"❌ FAIL: 'source' column missing. Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_source_column_exists()
