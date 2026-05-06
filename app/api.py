from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.services.extraction import ExtractionService
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService
from app.schemas.food_schemas import FoodLog
import json

app = FastAPI(title="MacroManager API")
db_manager = DatabaseManager()
foodbank_service = FoodbankService(db_manager)
extraction_service = ExtractionService(foodbank_service)

class LogRequest(BaseModel):
    text: str
    meal_type: str = "General"

@app.post("/log")
async def log_meal(request: LogRequest):
    try:
        meal_data = await extraction_service.parse(request.text)
        data = meal_data.model_dump()
        total_p = sum(item['macros']['protein'] for item in data['items'])
        total_c = sum(item['macros']['carbs'] for item in data['items'])
        total_f = sum(item['macros']['fat'] for item in data['items'])
        total_cal = sum(item['cals'] for item in data['items'])
        
        def sum_sub(key):
            return sum((item.get('sub_macros') or {}).get(key, 0) or 0 for item in data['items'])
            
        with db_manager.get_macros_conn() as conn:
            conn.execute(
                "INSERT INTO meals (meal_id, items_json, total_protein, total_carbs, total_fat, total_cals, total_fiber, total_sugar, total_saturated_fat, total_unsaturated_fat, meal_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (data['meal_id'], json.dumps(data['items']), total_p, total_c, total_f, total_cal, sum_sub('fiber'), sum_sub('sugar'), sum_sub('saturated_fat'), sum_sub('unsaturated_fat'), request.meal_type)
            )
            conn.commit()
        return {"status": "success", "message": f"Meal {meal_data.meal_id} logged successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/summary")
async def get_summary():
    with db_manager.get_macros_conn() as conn:
        cursor = conn.execute("SELECT total_protein, total_carbs, total_fat, total_cals, total_fiber, total_sugar, total_saturated_fat, total_unsaturated_fat, meal_type, items_json FROM meals WHERE date(timestamp) = date('now')")
        rows = cursor.fetchall()
        
        consumed = {k: sum(row[i] for row in rows) for i, k in enumerate(['protein', 'carbs', 'fat', 'calories', 'fiber', 'sugar', 'sat_fat', 'unsat_fat'])}
        grouped = {}
        for row in rows:
            m_type = row['meal_type'] or "General"
            if m_type not in grouped: grouped[m_type] = []
            grouped[m_type].append(json.loads(row['items_json']))
            
        return {
            "consumed": consumed, 
            "goals": db_manager.get_daily_goals(), 
            "grouped": grouped
        }

@app.get("/meals")
async def get_meals():
    with db_manager.get_macros_conn() as conn:
        cursor = conn.execute("SELECT id, meal_id, timestamp, items_json FROM meals WHERE date(timestamp) = date('now')")
        return [{"id": r[0], "meal_id": r[1], "timestamp": r[2], "items": json.loads(r[3])} for r in cursor.fetchall()]

@app.delete("/clear")
async def clear_data():
    with db_manager.get_macros_conn() as conn:
        conn.execute("DELETE FROM meals WHERE date(timestamp) = date('now')")
        conn.commit()
        return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

