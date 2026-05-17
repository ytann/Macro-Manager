#!/usr/bin/env python3
"""
Sprint 8 Database Migration Script
Migrates foods table to include reported_qty and per_100g columns.
Any food without a reported_qty is dropped (per requirements).
"""

import sqlite3
import sys
import os
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.core.config import Config

def migrate_db():
    db_path = Config.FOODBANK_DB_PATH
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("🔄 Sprint 8 Database Migration")
    print(f"📊 Source DB: {db_path}")
    print(f"💾 Backup will be created at: {backup_path}")
    
    try:
        # 1. Create backup
        conn = sqlite3.connect(db_path)
        backup_conn = sqlite3.connect(backup_path)
        conn.backup(backup_conn)
        backup_conn.close()
        print("✓ Backup created successfully")
        
        # 2. Check if columns already exist
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(foods)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'reported_cal' in columns:
            print("⚠️  Columns already exist. Skipping migration.")
            conn.close()
            return True
        
        # 3. Since FTS tables can't be altered, we need to recreate the table
        print("🔧 Recreating FTS table with new columns...")
        
        # Backup existing data
        cursor.execute("SELECT * FROM foods")
        rows = cursor.fetchall()
        print(f"   Backing up {len(rows)} existing food entries...")
        
        # Get column names
        cursor.execute("PRAGMA table_info(foods)")
        old_columns = [row[1] for row in cursor.fetchall()]
        print(f"   Old columns: {old_columns}")
        
        # Drop old table
        cursor.execute("DROP TABLE IF EXISTS foods")
        conn.commit()
        print("   ✓ Old table dropped")
        
        # Create new FTS table with new columns
        new_schema = """
            CREATE VIRTUAL TABLE IF NOT EXISTS foods USING fts5(
                name, aliases, calories UNINDEXED, protein UNINDEXED, 
                carbs UNINDEXED, fat UNINDEXED, fiber UNINDEXED, 
                sugar UNINDEXED, saturated_fat UNINDEXED, unsaturated_fat UNINDEXED,
                is_complete_protein UNINDEXED,
                verified UNINDEXED, source UNINDEXED,
                reported_qty UNINDEXED, reported_p UNINDEXED, reported_c UNINDEXED,
                reported_f UNINDEXED, p_per_100 UNINDEXED, c_per_100 UNINDEXED, f_per_100 UNINDEXED,
                reported_cal UNINDEXED, cal_per_100 UNINDEXED, reported_fiber UNINDEXED, fiber_per_100 UNINDEXED
            )
        """
        cursor.execute(new_schema)
        conn.commit()
        print("   ✓ New FTS table created")
        
        # 4. Restore data with normalization
        print("📈 Restoring and normalizing data...")
        insert_count = 0
        for row in rows:
            # Check row length to handle multiple migrations gracefully
            if len(row) == 13: # Pre-Sprint 8
                name, aliases, calories, protein, carbs, fat, fiber, sugar, sat_fat, unsat_fat, is_complete, verified, source = row
                reported_qty = 100.0
                reported_p = protein
                reported_c = carbs
                reported_f = fat
                p_per_100 = protein
                c_per_100 = carbs
                f_per_100 = fat
                reported_cal = calories
                cal_per_100 = calories
                reported_fiber = fiber
                fiber_per_100 = fiber
            elif len(row) == 20: # Sprint 8 Initial
                name, aliases, calories, protein, carbs, fat, fiber, sugar, sat_fat, unsat_fat, is_complete, verified, source, reported_qty, reported_p, reported_c, reported_f, p_per_100, c_per_100, f_per_100 = row
                reported_cal = calories
                cal_per_100 = calories
                reported_fiber = fiber
                fiber_per_100 = fiber
            else: # Sprint 8 Update
                name, aliases, calories, protein, carbs, fat, fiber, sugar, sat_fat, unsat_fat, is_complete, verified, source, reported_qty, reported_p, reported_c, reported_f, p_per_100, c_per_100, f_per_100, reported_cal, cal_per_100, reported_fiber, fiber_per_100 = row
            
            cursor.execute(
                """INSERT INTO foods (name, aliases, calories, protein, carbs, fat, fiber, sugar, 
                   saturated_fat, unsaturated_fat, is_complete_protein, verified, source,
                   reported_qty, reported_p, reported_c, reported_f, p_per_100, c_per_100, f_per_100,
                   reported_cal, cal_per_100, reported_fiber, fiber_per_100)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, aliases, calories, protein, carbs, fat, fiber, sugar, sat_fat, unsat_fat, 
                 is_complete, verified, source, reported_qty, reported_p, reported_c, reported_f,
                 p_per_100, c_per_100, f_per_100, reported_cal, cal_per_100, reported_fiber, fiber_per_100)
            )
            insert_count += 1
        
        conn.commit()
        print(f"   ✓ Restored {insert_count} entries with normalized values")
        
        # 5. Verify
        cursor.execute("SELECT COUNT(*) FROM foods")
        final_count = cursor.fetchone()[0]
        
        if final_count == insert_count:
            print(f"✓ Verification passed: All {final_count} entries migrated")
            print("\n✅ Migration completed successfully!")
            conn.close()
            return True
        else:
            print(f"⚠️  Warning: Expected {insert_count} entries, got {final_count}")
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print(f"📌 Your backup is at: {backup_path}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_db()
    sys.exit(0 if success else 1)
