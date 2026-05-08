import sys
import os
import ast
sys.path.append(os.getcwd())

def test_ingest_insert_logic():
    script_path = "scripts/ingest_csv.py"
    with open(script_path, "r") as f:
        code = f.read()
    
    # Look for the INSERT statement
    if "INSERT INTO foods" in code and "verified" not in code:
        print("❌ FAIL: INSERT statement in ingest_csv.py does not include 'verified' column.")
    elif "verified" in code:
        print("✅ PASS: 'verified' mentioned in ingest_csv.py.")
    else:
        print("❌ FAIL: No INSERT statement found.")

if __name__ == "__main__":
    test_ingest_insert_logic()
