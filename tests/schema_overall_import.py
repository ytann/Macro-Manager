import sys
import os
import sqlite3
sys.path.append(os.getcwd())
import subprocess

def test_overall_import_verified_status():
    csv_path = "test_verified_import.csv"
    with open(csv_path, "w") as f:
        f.write("name,aliases,calories,protein,carbs,fat,fiber\nBanana,kela,89,1.1,23,0.3,2.6")
    
    try:
        subprocess.run(["python3", "scripts/ingest_csv.py", csv_path], capture_output=True)
        
        conn = sqlite3.connect("foodbank.db")
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT verified FROM foods WHERE name = 'Banana'").fetchone()
        conn.close()
        
        if row and row['verified'] == 0:
            print("✅ PASS: Imported item correctly initialized with verified=0.")
        elif row is None:
            print("❌ FAIL: Item not imported.")
        else:
            print(f"❌ FAIL: Unexpected verified status: {row['verified']}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        if os.path.exists(csv_path): os.remove(csv_path)

if __name__ == "__main__":
    test_overall_import_verified_status()
