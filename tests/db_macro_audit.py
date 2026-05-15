import sqlite3
import os
from app.core.config import Config

def check_db_health():
    db_path = Config.FOODBANK_DB_PATH
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- Database Health Check ---")
    
    # 1. Check for Zeros
    cursor.execute("SELECT COUNT(*) FROM foods")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM foods WHERE calories = 0 OR calories IS NULL")
    zeros = cursor.fetchone()[0]
    
    print(f"Total items: {total}")
    print(f"Items with 0/NULL calories: {zeros} ({ (zeros/total*100 if total > 0 else 0):.2f}%)")

    # 2. Compare Air Fried vs Fried
    print("\n--- Air Fried vs Fried Comparison ---")
    
    # Find common food names that have both versions
    # This is a bit tricky with SQL, so we'll fetch all and compare in Python
    cursor.execute("SELECT name, calories, fat FROM foods")
    foods = cursor.fetchall()
    
    comparisons = []
    for i in range(len(foods)):
        for j in range(i + 1, len(foods)):
            name1, cal1, fat1 = foods[i]
            name2, cal2, fat2 = foods[j]
            
            # Look for "Air Fried X" and "Fried X"
            if "air fried" in name1.lower() and "fried" in name2.lower() and "air fried" not in name2.lower():
                base1 = name1.lower().replace("air fried", "").strip()
                base2 = name2.lower().replace("fried", "").strip()
                if base1 == base2 and base1 != "":
                    comparisons.append({
                        "item": base1,
                        "air_fried": {"cal": cal1, "fat": fat1},
                        "fried": {"cal": cal2, "fat": fat2}
                    })
            elif "air fried" in name2.lower() and "fried" in name1.lower() and "air fried" not in name1.lower():
                base1 = name2.lower().replace("air fried", "").strip()
                base2 = name1.lower().replace("fried", "").strip()
                if base1 == base2 and base1 != "":
                    comparisons.append({
                        "item": base1,
                        "air_fried": {"cal": cal2, "fat": fat2},
                        "fried": {"cal": cal1, "fat": fat1}
                    })

    if not comparisons:
        print("No Air Fried vs Fried pairs found in database.")
    else:
        for comp in comparisons:
            item = comp['item']
            af_cal = comp['air_fried']['cal']
            f_cal = comp['fried']['cal']
            af_fat = comp['air_fried']['fat']
            f_fat = comp['fried']['fat']
            
            status = "✅" if af_cal < f_cal else "❌"
            print(f"{status} {item}: AirFried({af_cal}cal, {af_fat}g fat) vs Fried({f_cal}cal, {f_fat}g fat)")

    conn.close()

if __name__ == "__main__":
    check_db_health()
