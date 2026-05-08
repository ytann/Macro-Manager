import sys
import os
import sqlite3
sys.path.append(os.getcwd())
from app.services.database import DatabaseManager

def test_singleton_path_clash():
    # Attempt to create two managers with different DB paths
    # Since it's a singleton, the second one will just return the first one.
    try:
        db1 = DatabaseManager()
        # We can't pass path to __init__ currently because it's a singleton using Config
        # But we can check if we can force a different path
        db1.foodbank_path = "db1.db"
        
        db2 = DatabaseManager()
        db2.foodbank_path = "db2.db"
        
        if db1.foodbank_path == db2.foodbank_path:
            print("❌ FAIL: Second instance forced first instance's path (Singleton clash).")
        else:
            print("✅ PASS: Instances maintain separate paths.")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_singleton_path_clash()
