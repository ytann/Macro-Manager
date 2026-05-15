import sqlite3
from app.core.config import Config

def seed_comparison_data():
    db_path = Config.FOODBANK_DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Data to seed: (name, aliases, calories, protein, carbs, fat, fiber, sugar, sat_fat, unsat_fat, is_complete, verified, source)
    # Logic: Air Fried < Fried for cal and fat
    test_data = [
        ("Air Fried Chicken Thighs", "air fried chicken", 210, 25, 0, 11, 0, 0, 3, 8, 1, 1, "audit_seed"),
        ("Fried Chicken Thighs", "fried chicken", 280, 24, 2, 18, 0, 0, 6, 12, 1, 1, "audit_seed"),
        ("Air Fried Potato Wedges", "air fried potatoes", 120, 2, 22, 3, 3, 1, 0.5, 2.5, 0, 1, "audit_seed"),
        ("Fried Potato Wedges", "fried potatoes", 250, 2, 22, 15, 3, 1, 4, 11, 0, 1, "audit_seed"),
    ]
    
    for item in test_data:
        cursor.execute(
            "INSERT OR REPLACE INTO foods (name, aliases, calories, protein, carbs, fat, fiber, sugar, saturated_fat, unsaturated_fat, is_complete_protein, verified, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            item
        )
    
    conn.commit()
    conn.close()
    print("Seeded comparison data for audit.")

if __name__ == "__main__":
    seed_comparison_data()
