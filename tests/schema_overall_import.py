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
        # Provide inputs for the interactive prompts in ingest_csv.py
        # Mapping: Name: 0, Calories: 2, Protein: 3, Carbs: 4, Fat: 5, Fiber: 6, Complete: \n
        inputs = "0\n2\n3\n4\n5\n6\n\n"
        subprocess.run(["python3", "scripts/ingest_csv.py", csv_path], 
                       input=inputs, text=True, capture_output=True, check=True)
        
        conn = sqlite3.connect("foodbank.db")
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT verified FROM foods WHERE name = 'Banana'").fetchone()
        conn.close()
        
        assert row is not None, "Item not imported."
        assert row['verified'] == 0, f"Unexpected verified status: {row['verified']}"
        
    except Exception as e:
        if os.path.exists(csv_path): os.remove(csv_path)
        raise e
    finally:
        if os.path.exists(csv_path): os.remove(csv_path)

if __name__ == "__main__":
    test_overall_import_verified_status()
