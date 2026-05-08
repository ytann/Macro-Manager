import sys
import os
sys.path.append(os.getcwd())
from app.services.database import DatabaseManager

def test_singleton_identity():
    db1 = DatabaseManager()
    db2 = DatabaseManager()
    
    if db1 is db2:
        print("❌ FAIL: DatabaseManager is a singleton (db1 is db2).")
    else:
        print("✅ PASS: DatabaseManager allows multiple instances.")

if __name__ == "__main__":
    test_singleton_identity()
