import sqlite3
import sys

def calculate_per_100(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        updates = [
            ('p_per_100', 'reported_p'),
            ('c_per_100', 'reported_p'), # Wait, this should be reported_c
            ('c_per_100', 'reported_c'),
            ('f_per_100', 'reported_f'),
            ('cal_per_100', 'reported_cal'),
            ('fiber_per_100', 'reported_fiber'),
        ]
        
        # Re-correcting the mapping
        mappings = {
            'p_per_100': 'reported_p',
            'c_per_100': 'reported_c',
            'f_per_100': 'reported_f',
            'cal_per_100': 'reported_cal',
            'fiber_per_100': 'reported_fiber',
        }

        print(f"Calculating per-100g macros for {db_path}...")
        for target, source in mappings.items():
            print(f"  - Updating {target} using {source}")
            query = f"""
            UPDATE foods 
            SET {target} = ROUND(({source} * 100.0) / reported_qty, 2)
            WHERE reported_qty > 0;
            """
            cursor.execute(query)
        
        conn.commit()
        print("Successfully updated per-100g macro columns.")
        
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    calculate_per_100('foodbank.db')
