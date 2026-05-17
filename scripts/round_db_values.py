import sqlite3
import sys

def round_db_values(db_path):
    columns_to_round = [
        'calories', 'protein', 'carbs', 'fat', 'fiber', 'sugar', 'saturated_fat', 'unsaturated_fat',
        'reported_qty', 'reported_p', 'reported_c', 'reported_f', 'p_per_100', 'c_per_100', 'f_per_100',
        'reported_cal', 'cal_per_100', 'reported_fiber', 'fiber_per_100'
    ]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"Rounding values in {db_path}...")
        for col in columns_to_round:
            print(f"  - Rounding column: {col}")
            query = f"UPDATE foods SET {col} = ROUND({col}, 2)"
            cursor.execute(query)
        
        conn.commit()
        print("All specified columns have been rounded to 2 decimal places.")
        
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    round_db_values('foodbank.db')
