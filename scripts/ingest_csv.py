import pandas as pd
import sqlite3
import os
import sys

# Add app directory to path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.core.config import Config

DB_PATH = Config.FOODBANK_DB_PATH

def ingest_csv():
    """
    Interactively maps CSV columns to Foodbank schema and ingests data into 
    the SQLite FTS5 database.
    """
    # Accept CSV path from command line if provided, otherwise prompt
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = input("Enter the path to the foods CSV file (default: foods.csv): ").strip() or "foods.csv"

    if not os.path.exists(csv_file):
        print(f"Error: File {csv_file} not found.")
        return

    try:
        # Read CSV using pandas
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    print("\n--- CSV Column Names ---")
    for i, col in enumerate(df.columns):
        print(f"{i}: {col}")
    print("------------------------\n")
    
    print("Map the CSV columns to Foodbank schema (Type the column name or index number):")
    
    def get_col(prompt):
        val = input(prompt).strip()
        if val.isdigit():
            idx = int(val)
            if 0 <= idx < len(df.columns):
                return df.columns[idx]
        if val in df.columns:
            return val
        print(f"Warning: '{val}' not found. Using None (will be skipped/zeroed).")
        return None

    mapping = {
        'name': get_col("Name: "),
        'calories': get_col("Calories: "),
        'protein': get_col("Protein: "),
        'carbs': get_col("Carbs: "),
        'fat': get_col("Fat: "),
        'fiber': get_col("Fiber: "),
        'complete': get_col("Is Complete Protein (Optional, press enter to skip): ")
    }

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure table exists with original FTS5 schema
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS foods USING fts5(
            name, aliases, calories UNINDEXED, protein UNINDEXED, 
            carbs UNINDEXED, fat UNINDEXED, fiber UNINDEXED, is_complete_protein UNINDEXED,
            verified UNINDEXED, source UNINDEXED
        )
    """)
    
    def safe_float(val):
        if val is None:
            return 0.0
        try:
            return float(val) if pd.notnull(val) else 0.0
        except (ValueError, TypeError):
            return 0.0

    def safe_bool(val):
        if val is None:
            return 0
        try:
            if isinstance(val, (bool, int)):
                return int(val)
            s = str(val).lower()
            return 1 if s in ['yes', 'true', '1', 'y'] else 0
        except (ValueError, TypeError):
            return 0

    count = 0
    for _, row in df.iterrows():
        try:
            name_col = mapping['name']
            if name_col is None:
                continue
            
            name = str(row[name_col])
            aliases = name.lower()
            
            cursor.execute(
                "INSERT INTO foods (name, aliases, calories, protein, carbs, fat, fiber, is_complete_protein, verified, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name, 
                    aliases, 
                    safe_float(row.get(mapping['calories'])), 
                    safe_float(row.get(mapping['protein'])), 
                    safe_float(row.get(mapping['carbs'])), 
                    safe_float(row.get(mapping['fat'])), 
                    safe_float(row.get(mapping['fiber'])), 
                    safe_bool(row.get(mapping['complete'])),
                    0,
                    'csv_import'
                )
            )
            count += 1
        except Exception:
            continue
            
    conn.commit()
    conn.close()
    print(f"\nSuccessfully ingested {count} items into Foodbank.")

if __name__ == "__main__":
    ingest_csv()
