from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict
from app.services.extraction import ExtractionService
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService
from app.services.onboarding import OnboardingService
from app.services.memory import MemoryService
from app.core import queries
from app.core.logger import logger
from app.schemas.food_schemas import GoalRequest, FoodItem
import json
import asyncio
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
onboarding_service = OnboardingService()
memory_service = MemoryService()

class LogRequest(BaseModel):
    text: str
    meal_type: str = "General"

class VisionLogRequest(BaseModel):
    base64_image: str
    environment: str = "Home"
    hint: str = ""

class OnboardRequest(BaseModel):
    bio_text: str

class MemoryRequest(BaseModel):
    text: str

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

@app.post("/onboard")
async def onboard(request: OnboardRequest):
    try:
        macros = await onboarding_service.calculate_pcos_baseline(request.bio_text)
        db_manager.set_daily_goals(
            protein=macros["protein"],
            carbs=macros["carbs"],
            fat=macros["fat"],
            calories=macros["calories"]
        )
        return {"status": "success", "macros": macros}
    except Exception as e:
        logger.error(f"Onboarding API Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
 
@app.delete("/clear")
async def clear_data():
    try:
        def _do_clear():
            with db_manager.get_macros_conn() as conn:
                conn.execute(queries.MEALS_DELETE_TODAY)
                conn.commit()
        
        await asyncio.to_thread(_do_clear)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Clear data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vision-log")
async def log_vision_meal(request: VisionLogRequest):
    try:
        meal_data = await extraction_service.extract_from_image(
            request.base64_image, request.environment, request.hint
        )

        totals = {
            'p': meal_data.total_macros.protein,
            'c': meal_data.total_macros.carbs,
            'f': meal_data.total_macros.fat,
            'cal': meal_data.total_calories
        }

        await _save_meal_to_db(meal_data.meal_id, meal_data.items, totals, "Vision")

        return {"status": "success", "message": f"Vision meal {meal_data.meal_id} logged successfully"}
    except Exception as e:
        logger.error(f"Vision API Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/memory")
async def update_memory(request: MemoryRequest):
    try:
        updated_content = await memory_service.update_memory(request.text)
        return {"status": "success", "content": updated_content}
    except Exception as e:
        logger.error(f"Memory API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory")
async def get_memory():
    try:
        with open(memory_service.memory_file, 'r') as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        logger.error(f"Memory Read Error: {e}")
        return {"content": ""}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

