from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.services.extraction import ExtractionService
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService
from app.schemas.food_schemas import FoodLog
import json
import asyncio
from contextlib import asynccontextmanager

async def heartbeat():
    while True:
        try:
            if await foodbank_service._is_network_available():
                count = await foodbank_service.get_pending_count()
                if count > 0:
                    print(f'Heartbeat: Internet detected. Processing {count} items...')
                    await foodbank_service.run_sync_cycle()
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Heartbeat Error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(heartbeat())
    yield
    task.cancel()

app = FastAPI(title="MacroManager API", lifespan=lifespan)
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
        print(f"DEBUG: meal_data type: {type(meal_data)}")
        
        total_p = meal_data.total_macros.protein
        total_c = meal_data.total_macros.carbs
        total_f = meal_data.total_macros.fat
        total_cal = meal_data.total_calories
        
        def sum_sub(key):
            total = 0.0
            for item in meal_data.items:
                if item.sub_macros:
                    val = getattr(item.sub_macros, key, 0)
                    total += val if val is not None else 0
            return total
            
        with db_manager.get_macros_conn() as conn:
            items_json = json.dumps([item.model_dump() for item in meal_data.items])
            conn.execute(
                "INSERT INTO meals (meal_id, items_json, total_protein, total_carbs, total_fat, total_cals, total_fiber, total_sugar, total_saturated_fat, total_unsaturated_fat, meal_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (meal_data.meal_id, items_json, total_p, total_c, total_f, total_cal, sum_sub('fiber'), sum_sub('sugar'), sum_sub('saturated_fat'), sum_sub('unsaturated_fat'), request.meal_type)
            )
            conn.commit()
        return {"status": "success", "message": f"Meal {meal_data.meal_id} logged successfully"}
    except Exception as e:
        print(f"API Error: {e}")
        import traceback
        traceback.print_exc()
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

@app.get("/pending-count")
async def get_pending_count():
    count = await foodbank_service.get_pending_count()
    return {"pending_count": count}

@app.get("/sync-status")
async def get_sync_status():
    last_sync = await foodbank_service.get_sync_timestamp()
    return {"last_sync": last_sync}

@app.post("/verify-queue")
async def verify_queue(background_tasks: BackgroundTasks):
    background_tasks.add_task(foodbank_service.run_sync_cycle)
    return {"status": "Queue processing started in background"}

@app.delete("/clear")
async def clear_data():

    with db_manager.get_macros_conn() as conn:
        conn.execute("DELETE FROM meals WHERE date(timestamp) = date('now')")
        conn.commit()
        return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

