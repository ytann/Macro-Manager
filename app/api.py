from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.parser import parse_food_log
from app.database import save_meal, get_todays_macros, init_db, get_todays_meals, clear_todays_meals, get_daily_goals

app = FastAPI(title="MacroManager API")

# Initialize DB on startup
init_db()

class LogRequest(BaseModel):
    """Request schema for logging a meal."""
    text: str
    meal_type: str = "General"

@app.post("/log")
async def log_meal(request: LogRequest):
    """
    Parses a natural language food log, calculates macros, 
    and saves the meal to the database.
    """
    try:
        meal_data = parse_food_log(request.text)
        save_meal(meal_data, meal_type=request.meal_type)
        return {"status": "success", "message": f"Meal {meal_data.meal_id} logged successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/summary")
async def get_summary():
    """Retrieves aggregated nutrition totals, grouped meals, and daily goals."""
    try:
        summary_data = get_todays_macros()
        goals = get_daily_goals()
        return {
            "consumed": summary_data["totals"],
            "grouped": summary_data["grouped"],
            "goals": goals
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/meals")
async def get_meals():
    """Retrieves a list of all individual meals logged today."""
    try:
        return get_todays_meals()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clear")
async def clear_data():
    """Deletes all meal logs for the current day."""
    try:
        clear_todays_meals()
        return {"status": "success", "message": "Daily data cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

