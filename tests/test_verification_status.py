import sys
import os
sys.path.append(os.getcwd())
from app.services.database import DatabaseManager

def check_verified_foods():
    """
    Fetches and prints all food items from the foodbank that have been verified.
    """
    db = DatabaseManager()
    conn = db.get_foodbank_conn()
    cursor = conn.cursor()
    
    print("🔍 Fetching Verified Food Items from Database...\n")
    
    try:
        # Query for all items where verified = 1
        cursor.execute("SELECT name, calories, protein, carbs, fat, fiber FROM foods WHERE verified = 1")
        verified_foods = cursor.fetchall()
        
        if not verified_foods:
            print("No verified food items found in the database yet.")
            return
            
        print(f"{'Food Name':<20} | {'Cals':<8} | {'Prot':<8} | {'Carbs':<8} | {'Fat':<8} | {'Fiber':<8}")
        print("-" * 65)
        
        for row in verified_foods:
            print(f"{row['name']:<20} | {row['calories']:<8.1f} | {row['protein']:<8.1f} | {row['carbs']:<8.1f} | {row['fat']:<8.1f} | {row['fiber']:<8.1f}")
            
        print(f"\nTotal Verified Items: {len(verified_foods)}")
        
    except Exception as e:
        print(f"❌ Error fetching verified foods: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_verified_foods()
