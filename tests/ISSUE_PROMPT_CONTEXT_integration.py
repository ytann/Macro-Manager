import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.extraction import ExtractionService
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_preservation_pipeline():
    # Setup
    db = MagicMock(spec=DatabaseManager)
    fb = FoodbankService(db)
    service = ExtractionService(fb)

    # Mock LLM responses
    voice_correction_resp = MagicMock()
    voice_correction_resp.choices = [
        MagicMock(message=MagicMock(content="I had Air Fried Chicken Breast and McDonalds Veg Burger"))
    ]

    extraction_resp = MagicMock()
    extraction_resp.choices = [
        MagicMock(message=MagicMock(content=json.dumps({
            "items": [
                {"name": "Air Fried Chicken Breast", "grams": 200},
                {"name": "McDonalds Veg Burger", "grams": 150}
            ]
        })))
    ]

    verification_resp = MagicMock()
    verification_resp.choices = [
        MagicMock(message=MagicMock(content=json.dumps({"missing": []})))
    ]

    # Mock Foodbank data
    food_data_map = {
        "air fried chicken breast": {"calories": 300, "protein": 60, "carbs": 0, "fat": 10, "verified": 1},
        "mcdonalds veg burger": {"calories": 400, "protein": 15, "carbs": 40, "fat": 20, "verified": 1},
    }

    with patch('litellm.acompletion', new_callable=AsyncMock) as mock_litellm, \
         patch.object(FoodbankService, 'get_nutrition_data', new_callable=AsyncMock) as mock_get_nutr, \
         patch.object(FoodbankService, 'get_recipe', new_callable=AsyncMock) as mock_get_recipe:
        
        mock_get_recipe.return_value = None 
        mock_litellm.side_effect = [
            voice_correction_resp,
            extraction_resp,
            verification_resp
        ]
        mock_get_nutr.side_effect = lambda name: food_data_map.get(name.lower())

        test_text = "I had Air Fried Chicken Breast and McDonalds Veg Burger"
        log = await service.parse(test_text, meal_id="test_123")

        # Verify items
        names = [item.name for item in log.items]
        assert "Air Fried Chicken Breast" in names, "FAIL: Air Fried Chicken Breast was stripped"
        assert "McDonalds Veg Burger" in names, "FAIL: McDonalds Veg Burger was stripped"
        
        print("PASS: Context preserved in extraction and resolved in foodbank")

if __name__ == "__main__":
    asyncio.run(test_preservation_pipeline())
