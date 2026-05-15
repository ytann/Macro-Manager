import pytest
import httpx
import asyncio
from app.services.database import DatabaseManager

API_URL = "http://127.0.0.1:8000"

@pytest.mark.asyncio
async def test_full_async_pipeline():
    """
    Integration test for the full async pipeline.
    Verify that starting a log and polling for completion results in correct DB state.
    """
    db = DatabaseManager()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Start a log for a known item
        payload = {
            "text": "100g Apple",
            "meal_type": "Snack",
            "is_voice": False
        }
        resp = await client.post(f"{API_URL}/log/start", json=payload)
        assert resp.status_code == 200
        meal_id = resp.json()["meal_id"]
        
        # 2. Poll for completion
        max_attempts = 20
        completed = False
        for _ in range(max_attempts):
            await asyncio.sleep(1)
            status_resp = await client.get(f"{API_URL}/log/status/{meal_id}")
            if status_resp.json()["status"] == "completed":
                completed = True
                break
        
        assert completed, f"Meal {meal_id} did not complete resolution"
        
        # 3. Verify DB state
        with db.get_macros_conn() as conn:
            cursor = conn.execute("SELECT total_cals FROM meals WHERE meal_id = ?", (meal_id,))
            row = cursor.fetchone()
            assert row is not None, "Meal not found in DB"
            # Apple is 52 kcal per 100g
            assert row[0] == 52.0, f"Expected 52.0 kcal, got {row[0]}"

if __name__ == "__main__":
    asyncio.run(test_full_async_pipeline())
