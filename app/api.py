from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Dict
import asyncio
from contextlib import asynccontextmanager
from app.services.extraction import ExtractionService
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService
from app.services.onboarding import OnboardingService, OnboardingValidationError
from app.services.memory import MemoryService
from app.services.planner import PlannerService
from app.core import queries


from app.core.logger import logger
from app.schemas.food_schemas import GoalRequest, FoodItem
import json
def safe_json_loads(s):
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return []


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

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception occurred: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Our team has been notified."},
    )

app.mount("/static", StaticFiles(directory="app/static"), name="static")
db_manager = DatabaseManager()
foodbank_service = FoodbankService(db_manager)
extraction_service = ExtractionService(foodbank_service)
onboarding_service = OnboardingService()
memory_service = MemoryService()
planner_service = PlannerService()

class LogRequest(BaseModel):
    text: str = Field(..., max_length=5000)
    meal_type: str = "General"
    environment: str = "restaurant"  # home, restaurant, street food, packaged
    is_voice: bool = False

class VisionLogRequest(BaseModel):
    base64_image: str
    environment: str = "Home"
    hint: str = ""

class OnboardRequest(BaseModel):
    bio_text: str = Field(..., max_length=5000)

class MemoryRequest(BaseModel):
    text: str = Field(..., max_length=5000)

class PlannerRequest(BaseModel):
    user_query: str = Field(..., max_length=5000)
    remaining_macros: dict
    memory_context: str = Field("", max_length=10000)  # User's Sovereign Memory (up to 2000 tokens)

async def _save_meal_to_db(meal_id: str, items: List[FoodItem], totals: Dict[str, float], meal_type: str):
    def sum_sub(key):
        total = 0.0
        for item in items:
            if item.sub_macros:
                val = getattr(item.sub_macros, key, 0)
                total += val if val is not None else 0
        return total
    
    with db_manager.transaction('macros') as conn:
        items_json = json.dumps([item.model_dump() for item in items])
        conn.execute(
            queries.MEALS_INSERT,
            (meal_id, items_json, totals['p'], totals['c'], totals['f'], totals['cal'], sum_sub('fiber'), sum_sub('sugar'), sum_sub('saturated_fat'), sum_sub('unsaturated_fat'), meal_type)
        )

async def _process_and_save_meal(meal_id: str, items: List[dict], meal_type: str, environment: str = "restaurant"):
    try:
        logger.info(f"Background resolution started for meal {meal_id} (environment: {environment})")
        meal_data = await extraction_service.resolve_nutrition(items, meal_id)
        
        totals = {
            'p': meal_data.total_macros.protein,
            'c': meal_data.total_macros.carbs,
            'f': meal_data.total_macros.fat,
            'cal': meal_data.total_calories
        }
        
        await _save_meal_to_db(meal_data.meal_id, meal_data.items, totals, meal_type)
        logger.info(f"Background resolution completed for meal {meal_id}")
    except Exception as e:
        logger.error(f"Background resolution failed for meal {meal_id}: {e}")

@app.post("/log/start")
async def start_log_meal(request: LogRequest, background_tasks: BackgroundTasks):
    try:
        items, meal_id = await extraction_service.extract_items(request.text, request.is_voice)
        
        # Trigger background resolution
        background_tasks.add_task(_process_and_save_meal, meal_id, items, request.meal_type, request.environment)
        
        return {
            "status": "processing",
            "meal_id": meal_id,
            "items": items,
            "environment": request.environment
        }
    except Exception as e:
        logger.error(f"Log Start Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/log/status/{meal_id}")
async def get_log_status(meal_id: str):
    with db_manager.get_macros_conn() as conn:
        # Check if the meal exists in the meals table
        cursor = conn.execute("SELECT 1 FROM meals WHERE meal_id = ?", (meal_id,))
        exists = cursor.fetchone()
        
    if exists:
        return {"status": "completed", "meal_id": meal_id}
    return {"status": "processing", "meal_id": meal_id}


@app.post("/log")
async def log_meal(request: LogRequest):
    try:
        import getpass
        logger.info(f"User running API: {getpass.getuser()}")
        
        meal_data = await extraction_service.parse(request.text, meal_id=request.text[:10], is_voice=request.is_voice)
        
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
async def get_summary(date: str = Query(None, description="Date in YYYY-MM-DD format")):
    with db_manager.get_macros_conn() as conn:
        if date:
            cursor = conn.execute(queries.MEALS_GET_FULL_BY_DATE, (date,))
        else:
            cursor = conn.execute(queries.MEALS_GET_TODAY_FULL)
        rows = cursor.fetchall()
        
        consumed = {k: sum(row[i] or 0 for row in rows) for i, k in enumerate(['protein', 'carbs', 'fat', 'calories', 'fiber', 'sugar', 'saturated_fat', 'unsaturated_fat'])}
        grouped = {}
        for row in rows:
            m_type = row['meal_type'] or "General"
            if m_type not in grouped:
                grouped[m_type] = []
            grouped[m_type].append(safe_json_loads(row['items_json']))
            
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

@app.delete("/meals/clear")
async def clear_meals(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    with db_manager.get_macros_conn() as conn:
        conn.execute(queries.MEALS_DELETE_BY_DATE, (date,))
        conn.commit()
    return {"status": "success", "message": f"Cleared meals for {date}"}

@app.get("/meals")
async def get_meals(date: str = Query(None, description="Date in YYYY-MM-DD format"), meal_type: str = Query(None)):
    with db_manager.get_macros_conn() as conn:
        if date:
            cursor = conn.execute(queries.MEALS_GET_IDS_BY_DATE, (date,))
        else:
            # Use a formatted string for the default 'now' query
            query_now = queries.MEALS_GET_IDS_BY_DATE.replace('?', "date('now', 'localtime')")
            cursor = conn.execute(query_now)
        
        meals = [{"id": r[0], "meal_id": r[1], "timestamp": r[2], "items": safe_json_loads(r[3]), "type": r[4]} for r in cursor.fetchall()]
        
        if meal_type and meal_type != "All":
            meals = [m for m in meals if m["type"] == meal_type]
            
        return meals


@app.delete("/meals/{meal_id}")
async def delete_meal(meal_id: int):
    try:
        with db_manager.get_macros_conn() as conn:
            conn.execute(queries.MEALS_DELETE_BY_ID, (meal_id,))
            conn.commit()
        return {"status": "success", "message": f"Meal {meal_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class UpdateMealRequest(BaseModel):
    items: List[FoodItem]

@app.patch("/meals/{meal_id}")
async def update_meal(meal_id: int, request: UpdateMealRequest):
    try:
        items = request.items
        # Recalculate totals
        def sum_val(key):
            return sum((getattr(item.sub_macros, key, 0) or 0) for item in items if item.sub_macros)
            
        total_p = sum(item.macros.protein for item in items)
        total_c = sum(item.macros.carbs for item in items)
        total_f = sum(item.macros.fat for item in items)
        total_cal = sum(item.cals for item in items)
        
        fiber = sum_val('fiber')
        sugar = sum_val('sugar')
        sat_fat = sum_val('saturated_fat')
        unsat_fat = sum_val('unsaturated_fat')
        
        items_json = json.dumps([item.model_dump() for item in items])
        
        with db_manager.get_macros_conn() as conn:
            conn.execute(
                queries.MEALS_UPDATE,
                (items_json, total_p, total_c, total_f, total_cal, fiber, sugar, sat_fat, unsat_fat, meal_id)
            )
            conn.commit()
            
        return {"status": "success", "message": f"Meal {meal_id} updated"}
    except Exception as e:
        logger.error(f"Update Meal Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

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
        macros = await onboarding_service.calculate_pmos_baseline(request.bio_text)
        db_manager.set_daily_goals(
            protein=macros["protein"],
            carbs=macros["carbs"],
            fat=macros["fat"],
            calories=macros["calories"]
        )
        return {"status": "success", "macros": macros}
    except OnboardingValidationError as e:
        logger.error(f"Onboarding Validation Error: {e.errors}")
        raise HTTPException(status_code=422, detail={"message": "Invalid or missing biometrics", "errors": e.errors})
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

@app.post("/planner")
async def ask_copilot(req: PlannerRequest):
    suggestion = await planner_service.generate_suggestion(req.user_query, req.remaining_macros, req.memory_context)
    return {"suggestion": suggestion}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

