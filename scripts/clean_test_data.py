import sqlite3
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, '..', 'foodbank.db')

def clean_db():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Delete entries that were added for testing (typically have NULL source or category)
        cursor.execute("DELETE FROM foods WHERE source IS NULL OR source = ''")
        
        # Also, let's remove the dummy entries that were added with single names
        dummies = ("Egg", "Soya", "Bacon")
        cursor.execute(f"DELETE FROM foods WHERE name IN {dummies}")

        conn.commit()
        print(f"Cleaned {cursor.rowcount} test entries from the database.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    clean_db()
