import sys
import os
import sqlite3
sys.path.append(os.getcwd())
from scripts.ingest_csv import ingest_csv # Assuming this function exists in the script

def test_ingest_csv_schema_missing():
    # Setup a temp db for ingestion
    db_path = "test_ingest.db"
    if os.path.exists(db_path): os.remove(db_path)
    
    # We'll mock the CSV path or use a small dummy CSV
    csv_path = "test_foods.csv"
    with open(csv_path, "w") as f:
        f.write("name,aliases,calories,protein,carbs,fat,fiber\nApple,seb,52,0.3,14,0.2,2.4")
    
    try:
        # Call the ingestion script logic (might need to wrap it in a function)
        # Since ingest_csv.py is likely a script, we might need to import and call a function
        # If it's just a script, we can use subprocess
        import subprocess
        subprocess.run(["python3", "scripts/ingest_csv.py", csv_path], capture_output=True)
        
        conn = sqlite3.connect("foodbank.db") # ingest_csv likely uses the default
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(foods)")
        cols = [row[1] for row in cursor.fetchall()]
        conn.close()
        
        if 'verified' not in cols:
            print("❌ FAIL: 'verified' column missing after CSV ingestion.")
        else:
            print("✅ PASS: 'verified' column exists.")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        if os.path.exists(csv_path): os.remove(csv_path)
        if os.path.exists(db_path): os.remove(db_path)

if __name__ == "__main__":
    test_ingest_csv_schema_missing()
