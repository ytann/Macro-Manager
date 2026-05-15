import pytest
import httpx
import asyncio
from app.core.config import Config

API_URL = "http://127.0.0.1:8000"

@pytest.mark.asyncio
async def test_log_start_endpoint():
    """
    Verify that /log/start extracts items and returns a meal_id immediately.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "text": "50g Budhani Chips, Egg Plant Parmesan",
            "meal_type": "Breakfast",
            "is_voice": False
        }
        
        start_time = asyncio.get_event_loop().time()
        response = await client.post(f"{API_URL}/log/start", json=payload)
        end_time = asyncio.get_event_loop().time()
        
        duration = end_time - start_time
        
        # Assertions
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        data = response.json()
        
        assert "meal_id" in data, "Response should contain meal_id"
        assert "items" in data, "Response should contain extracted items"
        assert len(data["items"]) >= 2, "Should have extracted at least 2 items"
        
        # The extraction should be fast (reasonable for local LLM)
        assert duration < 20.0, f"Extraction too slow: {duration:.4f}s"

if __name__ == "__main__":
    asyncio.run(test_log_start_endpoint())
