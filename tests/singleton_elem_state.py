import sys
import os
sys.path.append(os.getcwd())
from app.services.database import DatabaseManager

def test_singleton_state_leak():
    # If it's a singleton, changing state in db1 affects db2
    db1 = DatabaseManager()
    db2 = DatabaseManager()
    
    # We can't easily change "state" unless we add a dummy attribute
    db1.test_attr = "value1"
    
    if hasattr(db2, 'test_attr') and db2.test_attr == "value1":
        print("❌ FAIL: State leak detected. db2 reflects changes made to db1.")
    else:
        print("✅ PASS: No state leak between instances.")

if __name__ == "__main__":
    test_singleton_state_leak()
