import pandas as pd
import sqlite3
import re
import os
import sys

# Add app root to path for service imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

def normalize_name(name):
    # Convert to lowercase
    name = name.lower()
    # Remove content in parentheses
    name = re.sub(r'\(.*\)', '', name).strip()
    # Remove special characters
    name = re.sub(r'[^\w\s]', '', name)
    # Tokenize, sort, and rejoin
    return ' '.join(sorted(name.split()))

async def ingest_master_db(file_path):
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file_path = os.path.join(log_dir, 'deduplication_report.txt')

    try:
        xls = pd.ExcelFile(file_path)
        sheet1_name = xls.sheet_names[0]
        sheet2_name = xls.sheet_names[1]

        # --- Correctly parse the malformed "CSV-in-Excel" ---
        def parse_sheet(xls, sheet_name):
            sheet = xls.parse(sheet_name=sheet_name)
            header_list = sheet.columns[0].split(',')
            
            data = []
            for item in sheet.iloc[:, 0]:
                try:
                    data.append(item.split(','))
                except AttributeError: # Handles empty rows
                    continue

            df = pd.DataFrame(data, columns=header_list)
            return df

        df1 = parse_sheet(xls, sheet1_name)
        df2 = parse_sheet(xls, sheet2_name)
        
        # Strip any whitespace from column names
        df1.columns = df1.columns.str.strip()
        df2.columns = df2.columns.str.strip()
        print(f"DF1 Columns after parse: {df1.columns.tolist()}")
        print(f"DF2 Columns after parse: {df2.columns.tolist()}")

        # --- Data Processing ---
        
        # 1. Create display names for both dataframes
        df1.dropna(subset=['Food Item', 'Preparation Type'], inplace=True)
        df2.dropna(subset=['Food Item', 'Preparation Type'], inplace=True)
        df1['display_name'] = df1.apply(lambda row: f"{row['Food Item']} ({row['Preparation Type']})", axis=1)
        df2['display_name'] = df2.apply(lambda row: f"{row['Food Item']} ({row['Preparation Type']})", axis=1)

        # 2. Combine them
        df_all = pd.concat([df1, df2], ignore_index=True)
        
        # 3. Deduplicate the combined dataframe
        df_unique_all = df_all.drop_duplicates(subset=['display_name'])

        # 4. Handle PMOS specific data separately for the pmos_db
        pmos_unique = df2.drop_duplicates(subset=['display_name'])
        pmos_food_names = pmos_unique['display_name'].tolist()

        # Log duplicates
        duplicates = df_all[df_all.duplicated(subset=['display_name'], keep=False)]
        with open(log_file_path, 'w') as f:
            f.write("--- Deduplication Report ---\n")
            f.write(f"Found and removed {len(df_all) - len(df_unique_all)} duplicates based on 'display_name'.\n\n")
            f.write("Kept Entries (showing display_name):\n")
            f.write(df_unique_all[['display_name']].to_string())
            f.write("\n\nDropped Entries (showing display_name):\n")
            f.write(duplicates[['display_name']].to_string())

        print(f"Deduplication complete. Report saved to {log_file_path}")

        # --- DB Operations ---
        db_manager = DatabaseManager()
        foodbank_service = FoodbankService(db_manager)
        
        # 1. Wipe and Populate foodbank.db
        print("Wiping existing foodbank.db...")
        await asyncio.to_thread(db_manager.run_foodbank, "DELETE FROM foods", commit=True)
        
        print(f"Populating foodbank.db with {len(df_unique_all)} unique items...")
        for _, row in df_unique_all.iterrows():
            # Use a try-except block to catch rows with bad data
            try:
                await foodbank_service.normalize_and_upsert(
                    name=row['display_name'],
                    reported_qty=float(row['Quantity Reported (g)']),
                    protein=float(row['Protein Reported (g)']),
                    carbs=float(row['Carbs Reported (g)']),
                    fat=float(row['Fats Reported (g)']),
                    calories=float(row['Calories Reported (kcal)']),
                    fiber=float(row['Fiber Reported (g)']),
                    source='desk_research_v2',
                    verified=1
                )
            except (ValueError, TypeError) as e:
                print(f"Skipping row due to data error: {row['display_name']} - {e}", file=sys.stderr)

        print("foodbank.db population complete.")

        # 2. Create and Populate pmos_friendly_food.db
        def create_pmos_db():
            pmos_db_path = 'pmos_friendly_food.db'
            if os.path.exists(pmos_db_path):
                os.remove(pmos_db_path)
            
            print(f"Creating and populating {pmos_db_path} with {len(pmos_food_names)} items...")
            conn = sqlite3.connect(pmos_db_path)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE pmos_foods (name TEXT PRIMARY KEY)")
            for food_name in pmos_food_names:
                cursor.execute("INSERT OR IGNORE INTO pmos_foods (name) VALUES (?)", (food_name,))
            conn.commit()
            conn.close()
            print(f"{pmos_db_path} created successfully.")
		
        await asyncio.to_thread(create_pmos_db)
        
        foodbank_service.close()

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    if len(sys.argv) > 1:
        asyncio.run(ingest_master_db(sys.argv[1]))
    else:
        print("Usage: python ingest_master_db.py <file_path>", file=sys.stderr)
        sys.exit(1)
