import pandas as pd
import sqlite3
import re

def clean_food_name(name):
    if pd.isna(name):
        return None, None
    name = str(name)
    match = re.search(r'^(.*)\((.*)\)$', name)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    if " / " in name:
        parts = name.split(" / ", 1)
        return parts[0].strip(), parts[1].strip()
    return name.strip(), None

def get_food_category(name):
    if pd.isna(name):
        return "others"
    name = str(name).lower()
    categories = {
        "poultry": ["chicken", "turkey", "duck"],
        "red meat": ["mutton", "lamb", "beef", "pork", "goat"],
        "egg": ["egg"],
        "soya": ["soya", "tofu", "edamame"],
        "dairy": ["paneer", "cheese", "curd", "milk", "cream", "butter"],
        "seafood": ["fish", "prawn", "shrimp", "crab", "lobster", "salmon", "tuna"],
        "green veggies": ["cabbage", "peas", "cauliflower", "bottle gourd", "bitter gourd", "beans", "spinach", "broccoli", "lauki", "karela", "patta gobi", "aloo gobi", "matar", "brinjal", "okra", "lady finger", "capsicum", "carrot", "radish", "turnip", "beetroot", "gourd", "veg"]
    }
    for cat, keywords in categories.items():
        if any(kw in name for kw in keywords):
            return cat
    return "others"

def populate():
    df = pd.read_excel('Reference/master_fooddb.xlsx')
    num_cols_excel = ['Quantity Reported (g)', 'Calories Reported (kcal)', 'Protein Reported (g)', 'Carbs Reported (g)', 'Fats Reported (g)', 'Fiber Reported (g)']
    for col in num_cols_excel:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    rows = []
    for _, row in df.iterrows():
        food_item_raw = row['Food Item']
        food_item, alt_name = clean_food_name(food_item_raw)
        qty = row['Quantity Reported (g)']
        kcal = row['Calories Reported (kcal)']
        prot = row['Protein Reported (g)']
        carb = row['Carbs Reported (g)']
        fat = row['Fats Reported (g)']
        fib = row['Fiber Reported (g)']
        prep = row['Preparation Type']
        category = get_food_category(food_item_raw)
        
        if pd.notnull(qty) and qty != 0:
            kcal_100 = (kcal / qty) * 100 if pd.notnull(kcal) else None
            prot_100 = (prot / qty) * 100 if pd.notnull(prot) else None
            carb_100 = (carb / qty) * 100 if pd.notnull(carb) else None
            fat_100 = (fat / qty) * 100 if pd.notnull(fat) else None
            fib_100 = (fib / qty) * 100 if pd.notnull(fib) else None
        else:
            kcal_100 = prot_100 = carb_100 = fat_100 = fib_100 = None
            
        rows.append({
            'name': food_item,
            'aliases': alt_name,
            'calories': kcal_100, 'protein': prot_100, 'carbs': carb_100, 'fat': fat_100, 'fiber': fib_100,
            'sugar': 0.0, 'saturated_fat': 0.0, 'unsaturated_fat': 0.0, 'is_complete_protein': 0,
            'verified': 1, 'source': 'desk research', 'category': category,
            'reported_qty': qty, 'reported_p': prot, 'reported_c': carb, 'reported_f': fat,
            'p_per_100': prot_100, 'c_per_100': carb_100, 'f_per_100': fat_100,
            'reported_cal': kcal, 'cal_per_100': kcal_100, 'reported_fiber': fib, 'fiber_per_100': fib_100,
            'preparation_type': prep
        })
        
    final_df = pd.DataFrame(rows)
    num_cols_final = ['reported_qty', 'reported_cal', 'reported_p', 'reported_c', 'reported_f', 'reported_fiber', 'cal_per_100', 'p_per_100', 'c_per_100', 'f_per_100', 'fiber_per_100']
    for col in num_cols_final:
        final_df[col] = pd.to_numeric(final_df[col], errors='coerce').apply(lambda x: round(x, 1) if pd.notnull(x) else None)

    conn = sqlite3.connect('foodbank.db')
    conn.execute("DROP TABLE IF EXISTS foods")
    final_df.to_sql('foods', conn, if_exists='replace', index=False)
    conn.close()
    print("Database populated successfully with all columns.")

if __name__ == "__main__":
    populate()
