import asyncio
import json
import sys
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

sys.path.append(os.getcwd())

from app.api import app
from app.services.extraction import ExtractionService
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager
from app.schemas.food_schemas import FoodItem, FoodLog, Macros, SubMacros

client = TestClient(app)

# Mock data
DUMMY_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

@pytest.fixture
def service():
    db = DatabaseManager()
    fb = FoodbankService(db)
    return ExtractionService(fb)

@pytest.mark.asyncio
async def test_resolve_and_build_log_unit(service):
    # Test that _resolve_and_build_log correctly builds a FoodLog
    items_list = [
        {"name": "Chicken", "grams": 100},
        {"name": "Rice", "grams": 100},
    ]
    meal_id = "test_meal_123"
    
    # Mock nutrition for ingredients
    mock_nutrition = (
        {"p": 25.0, "c": 0.0, "f": 3.0, "cal": 150.0},
        FoodItem(
            name="Chicken", grams=100, cals=150.0,
            macros=Macros(protein=25.0, carbs=0.0, fat=3.0),
            verified=True
        )
    )
    
    with patch.object(service, '_get_nutrition_for_ingredient', new_callable=AsyncMock) as mock_nut:
        mock_nut.return_value = mock_nutrition
        
        log = await service._resolve_and_build_log(items_list, meal_id)
        
        assert isinstance(log, FoodLog)
        assert log.meal_id == meal_id
        assert len(log.items) == 2
        assert log.total_calories == 300.0 # 150 * 2
        assert log.total_macros.protein == 50.0 # 25 * 2
        assert mock_nut.call_count == 2

@pytest.mark.asyncio
async def test_resolve_and_build_log_empty_raises_error(service):
    with pytest.raises(ValueError, match="No valid food items extracted."):
        await service._resolve_and_build_log([], "test_meal")

@pytest.mark.asyncio
async def test_extract_from_image_returns_foodlog(service):
    # Test that extract_from_image now returns a FoodLog object
    mock_llm_response = {
        "items": [{"name": "Apple", "grams": 150}]
    }
    
    with patch('litellm.acompletion', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value.choices = [
            MagicMock(message=MagicMock(content=json.dumps(mock_llm_response)))
        ]
        
        # Mock _get_nutrition_for_ingredient to avoid DB/LLM calls inside the resolver
        with patch.object(service, '_get_nutrition_for_ingredient', new_callable=AsyncMock) as mock_nut:
            mock_nut.return_value = (
                {"p": 0.5, "c": 20.0, "f": 0.3, "cal": 80.0},
                FoodItem(name="Apple", grams=150, cals=80.0, macros=Macros(protein=0.5, carbs=20.0, fat=0.3), verified=True)
            )
            
            result = await service.extract_from_image(DUMMY_IMAGE, "Home", hint="It's a red apple")
            
            assert isinstance(result, FoodLog)
            assert "vision_" in result.meal_id
            assert len(result.items) == 1
            assert result.items[0].name == "Apple"

@pytest.mark.asyncio
async def test_extract_from_image_uses_hint(service):
    # Verify hint is passed to the prompt
    mock_llm_response = {"items": []}
    hint_text = "Focus on the salmon"
    
    with patch('litellm.acompletion', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value.choices = [
            MagicMock(message=MagicMock(content=json.dumps(mock_llm_response)))
        ]
        
        # We expect a ValueError if items is empty, so we catch it
        try:
            await service.extract_from_image(DUMMY_IMAGE, "Home", hint=hint_text)
        except ValueError:
            pass
            
        # Check if hint is in the prompt
        args, kwargs = mock_llm.call_args
        messages = kwargs.get('messages', [])[0].get('content', [])
        prompt_text = messages[0].get('text', '')
        assert hint_text in prompt_text

def test_vision_log_api_integration():
    # Test API endpoint end-to-end (with mocked service)
    from app.api import extraction_service
    
    mock_log = FoodLog(
        meal_id="vision_test",
        items=[FoodItem(name="Test", grams=100, cals=100, macros=Macros(protein=10, carbs=10, fat=10), verified=True)],
        total_macros=Macros(protein=10, carbs=10, fat=10),
        total_calories=100,
        confidence_score=1.0
    )
    
    with patch.object(extraction_service, 'extract_from_image', new_callable=AsyncMock) as mock_vision:
        mock_vision.return_value = mock_log
        
        payload = {
            "base64_image": DUMMY_IMAGE,
            "environment": "Home",
            "hint": "Test hint"
        }
        response = client.post("/vision-log", json=payload)
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_vision.assert_called_once_with(DUMMY_IMAGE, "Home", "Test hint")

@pytest.mark.asyncio
async def test_text_pipeline_regression(service):
    # Ensure text parsing still works after extracting the resolver
    text = "I had 2 eggs and a piece of toast"
    
    # Mock LLM responses for voice correction and main extraction
    with patch('litellm.acompletion', new_callable=AsyncMock) as mock_llm:
        # 1. Voice correction
        resp1 = MagicMock()
        resp1.choices = [MagicMock(message=MagicMock(content="I had 2 eggs and a piece of toast"))]
        
        # 2. Main extraction
        resp2 = MagicMock()
        extraction_data = {"items": [{"name": "Egg", "grams": 100}, {"name": "Toast", "grams": 50}]}
        resp2.choices = [MagicMock(message=MagicMock(content=json.dumps(extraction_data)))]
        
        mock_llm.side_effect = [resp1, resp2]

        
        with patch.object(service, '_get_nutrition_for_ingredient', new_callable=AsyncMock) as mock_nut:
            mock_nut.return_value = (
                {"p": 10.0, "c": 1.0, "f": 5.0, "cal": 100.0},
                FoodItem(name="Generic", grams=100, cals=100.0, macros=Macros(protein=10, carbs=1, fat=5), verified=True)
            )
            
            log = await service.parse(text)
            assert isinstance(log, FoodLog)
            assert len(log.items) >= 2
            assert log.total_calories > 0


if __name__ == "__main__":
    # Run tests manually if not using pytest
    async def run_all():
        s = service()
        print("Running unit tests...")
        await test_resolve_and_build_log_unit(s)
        print("PASS: test_resolve_and_build_log_unit")
        
        try:
            await test_resolve_and_build_log_empty_raises_error(s)
        except ValueError:
            print("PASS: test_resolve_and_build_log_empty_raises_error")
            
        await test_extract_from_image_returns_foodlog(s)
        print("PASS: test_extract_from_image_returns_foodlog")
        
        await test_extract_from_image_uses_hint(s)
        print("PASS: test_extract_from_image_uses_hint")
        
        test_vision_log_api_integration()
        print("PASS: test_vision_log_api_integration")
        
        await test_text_pipeline_regression(s)
        print("PASS: test_text_pipeline_regression")
        
        print("\nALL TESTS PASSED")

    asyncio.run(run_all())
