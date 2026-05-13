from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict
from app.services.extraction import ExtractionService
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService
from app.core import queries
from app.core.logger import logger
from app.schemas.food_schemas import GoalRequest, FoodItem, Macros, SubMacros
import json
import asyncio
import uuid
from contextlib import asynccontextmanager

async def heartbeat():
    while True:
        try:
            if await foodbank_service._is_network_available():
                count = await foodbank_service.get_pending_count()
                if count > 0:
                    logger.info(f'Heartbeat: Internet detected. Processing {count} items...')
                    await foodbank_service.run_sync_cycle()
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Heartbeat Error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(heartbeat())
    yield
    task.cancel()
    await foodbank_service.close()

app = FastAPI(title="MacroManager API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
db_manager = DatabaseManager()
foodbank_service = FoodbankService(db_manager)
extraction_service = ExtractionService(foodbank_service)

class LogRequest(BaseModel):
    text: str
    meal_type: str = "General"

class VisionLogRequest(BaseModel):
    base64_image: str
    environment: str = "Home"

async def _save_meal_to_db(meal_id: str, items: List[FoodItem], totals: Dict[str, float], meal_type: str):
    def sum_sub(key):
        total = 0.0
        for item in items:
            if item.sub_macros:
                val = getattr(item.sub_macros, key, 0)
                total += val if val is not None else 0
        return total

    with db_manager.get_macros_conn() as conn:
        items_json = json.dumps([item.model_dump() for item in items])
        conn.execute(
            queries.MEALS_INSERT,
            (meal_id, items_json, totals['p'], totals['c'], totals['f'], totals['cal'], sum_sub('fiber'), sum_sub('sugar'), sum_sub('saturated_fat'), sum_sub('unsaturated_fat'), meal_type)
        )
        conn.commit()

@app.post("/log")
async def log_meal(request: LogRequest):
    try:
        meal_data = await extraction_service.parse(request.text)
        
        totals = {
            'p': meal_data.total_macros.protein,
            'c': meal_data.total_macros.carbs,
            'f': meal_data.total_macros.fat,
            'cal': meal_data.total_calories
        }
        
        await _save_meal_to_db(meal_data.meal_id, meal_data.items, totals, request.meal_type)
        return {"status": "success", "message": f"Meal {meal_data.meal_id} logged successfully"}
    except Exception as e:
        logger.error(f"API Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/summary")
async def get_summary():
    with db_manager.get_macros_conn() as conn:
        cursor = conn.execute(queries.MEALS_GET_TODAY_FULL)
        rows = cursor.fetchall()
        
        consumed = {k: sum(row[i] or 0 for row in rows) for i, k in enumerate(['protein', 'carbs', 'fat', 'calories', 'fiber', 'sugar', 'saturated_fat', 'unsaturated_fat'])}
        grouped = {}
        for row in rows:
            m_type = row['meal_type'] or "General"
            if m_type not in grouped:
                grouped[m_type] = []
            grouped[m_type].append(json.loads(row['items_json']))
            
        daily_data = {
            "consumed": consumed, 
            "goals": db_manager.get_daily_goals(), 
            "grouped": grouped
        }
        
    weekly_data = db_manager.get_weekly_summary()
    return {
        "daily": daily_data,
        "weekly": weekly_data
    }

@app.get("/meals")
async def get_meals():
    with db_manager.get_macros_conn() as conn:
        cursor = conn.execute(queries.MEALS_GET_TODAY_IDS)
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
 
@app.post("/goals")
async def update_goals(request: GoalRequest):
    try:
        db_manager.set_daily_goals(
            protein=request.protein,
            carbs=request.carbs,
            fat=request.fat,
            calories=request.calories
        )
        return {"status": "success", "message": "Goals updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
@app.delete("/clear")
async def clear_data():

    with db_manager.get_macros_conn() as conn:
        conn.execute(queries.MEALS_DELETE_TODAY)
        conn.commit()
        return {"status": "success"}

@app.post("/vision-log")
async def log_vision_meal(request: VisionLogRequest):
    try:
        items = await extraction_service.extract_from_image(request.base64_image, request.environment)

        parsed_items = []
        state = {'p': 0.0, 'c': 0.0, 'f': 0.0, 'cal': 0.0}

        tasks = [
            extraction_service._get_nutrition_for_ingredient(
                item.get('name'), float(item.get('grams') or 0)
            )
            for item in items
        ]
        results = await asyncio.gather(*tasks)

        for result in results:
            if result is None:
                continue
            d, food_item = result
            for k in state:
                state[k] += d[k]
            parsed_items.append(food_item)

        if not parsed_items:
            raise ValueError("No valid food items extracted from image.")

        meal_id = f"vision_{uuid.uuid4().hex[:8]}"

        total_p = state['p']
        total_c = state['c']
        total_f = state['f']
        total_cal = state['cal']
        
        totals = {'p': total_p, 'c': total_c, 'f': total_f, 'cal': total_cal}
        await _save_meal_to_db(meal_id, parsed_items, totals, "Vision")

        return {"status": "success", "message": f"Vision meal {meal_id} logged successfully"}
    except Exception as e:

        logger.error(f"Vision API Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

