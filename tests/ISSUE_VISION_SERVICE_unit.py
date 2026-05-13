import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, patch
sys.path.append(os.getcwd())
from app.services.extraction import ExtractionService
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

def test_extract_from_image_returns_food_items():
    db = DatabaseManager()
    fb = FoodbankService(db)
    service = ExtractionService(fb)

    mock_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    mock_response = {
        "items": [
            {"name": "Chicken Curry", "grams": 350},
            {"name": "Steamed Rice", "grams": 200}
        ]
    }

    async def run():
        with patch('litellm.acompletion', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value.choices = [
                AsyncMock(message=AsyncMock(content=json.dumps(mock_response)))
            ]

            result = await service.extract_from_image(mock_image, "Home")

            assert isinstance(result, list), f"FAIL: expected list, got {type(result).__name__}"
            assert len(result) == 2, f"FAIL: expected 2 items, got {len(result)}"
            for item in result:
                assert isinstance(item, dict), f"FAIL: expected dict, got {type(item).__name__}"
                assert "name" in item, f"FAIL: item missing 'name': {item}"
                assert "grams" in item, f"FAIL: item missing 'grams': {item}"

            args, kwargs = mock_llm.call_args
            messages = kwargs.get('messages', [])
            assert len(messages) > 0, "FAIL: no messages sent to LLM"

            return True

    ok = asyncio.run(run())
    if ok:
        print("PASS: extract_from_image correctly returns list of food item dicts")


if __name__ == "__main__":
    test_extract_from_image_returns_food_items()