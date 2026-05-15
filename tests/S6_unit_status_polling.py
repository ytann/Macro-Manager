import pytest
import httpx
import asyncio
from app.core.config import Config

API_URL = "http://127.0.0.1:8000"

@pytest.mark.asyncio
async def test_log_status_polling():
    """
    Verify that /log/status/{meal_id} correctly tracks the resolution process.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Start a log
        payload = {
            "text": "Apple",
            "meal_type": "Snack",
            "is_voice": False
        }
        resp = await client.post(f"{API_URL}/log/start", json=payload)
        assert resp.status_code == 200
        meal_id = resp.json()["meal_id"]
        
        # 2. Immediate poll should be 'processing'
        status_resp = await client.get(f"{API_URL}/log/status/{meal_id}")
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "processing"
        
        # 3. Poll until completed or timeout
        max_attempts = 20
        completed = False
        for _ in range(max_attempts):
            await asyncio.sleep(1)
            status_resp = await client.get(f"{API_URL}/log/status/{meal_id}")
            if status_resp.json()["status"] == "completed":
                completed = True
                break
        
        assert completed, f"Meal {meal_id} did not complete resolution within {max_attempts} seconds"

if __name__ == "__main__":
    asyncio.run(test_log_status_polling())
