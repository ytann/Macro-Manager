import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.getcwd())

from app.api import app, extraction_service
from app.schemas.food_schemas import FoodItem, FoodLog, Macros, SubMacros

client = TestClient(app)
dummy_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

def test_log_endpoint_returns_success():
    mock_items = [
        {"name": "Chicken Curry", "grams": 350},
        {"name": "Steamed Rice", "grams": 200}
    ]
    
    mock_nutrition_result = (
        {"p": 30.0, "c": 40.0, "f": 15.0, "cal": 400.0},
        FoodItem(
            name="Chicken Curry", grams=350, cals=400.0,
            macros=Macros(protein=30.0, carbs=40.0, fat=15.0),
            sub_macros=SubMacros(fiber=2.0),
            verified=False
        )
    )

    with patch.object(extraction_service, 'parse', new_callable=AsyncMock) as mock_parse, \
         patch.object(extraction_service, '_get_nutrition_for_ingredient', new_callable=AsyncMock) as mock_nutrition:
        
        mock_parse.return_value = FoodLog(
            meal_id="test_meal_123",
            items=[
                FoodItem(name="Chicken Curry", grams=350, cals=400.0, macros=Macros(protein=30.0, carbs=40.0, fat=15.0), verified=False),
                FoodItem(name="Steamed Rice", grams=200, cals=260.0, macros=Macros(protein=5.0, carbs=55.0, fat=1.0), verified=False)
            ],
            total_macros=Macros(protein=35.0, carbs=95.0, fat=16.0),
            total_calories=660.0,
            confidence_score=1.0
        )
        mock_nutrition.return_value = (
            {"p": 30.0, "c": 40.0, "f": 15.0, "cal": 400.0},
            FoodItem(name="Chicken Curry", grams=350, cals=400.0, macros=Macros(protein=30.0, carbs=40.0, fat=15.0), verified=False)
        )

        payload = {"text": "I ate chicken curry and rice", "meal_type": "Lunch"}
        response = client.post("/log", json=payload)

        assert response.status_code == 200, f"FAIL: expected 200, got {response.status_code}: {response.text}"
        assert response.json()["status"] == "success"

def test_vision_log_endpoint_returns_success():
    mock_items = [
        {"name": "Chicken Curry", "grams": 350},
        {"name": "Steamed Rice", "grams": 200}
    ]
    
    mock_nutrition_result = (
        {"p": 30.0, "c": 40.0, "f": 15.0, "cal": 400.0},
        FoodItem(
            name="Chicken Curry", grams=350, cals=400.0,
            macros=Macros(protein=30.0, carbs=40.0, fat=15.0),
            sub_macros=SubMacros(fiber=2.0),
            verified=False
        )
    )

    with patch.object(extraction_service, 'extract_from_image', new_callable=AsyncMock) as mock_vision, \
         patch.object(extraction_service, '_get_nutrition_for_ingredient', new_callable=AsyncMock) as mock_nutrition:
        
        mock_vision.return_value = mock_items
        mock_nutrition.return_value = mock_nutrition_result

        payload = {"base64_image": dummy_base64, "environment": "Home"}
        response = client.post("/vision-log", json=payload)

        assert response.status_code == 200, f"FAIL: expected 200, got {response.status_code}: {response.text}"
        assert response.json()["status"] == "success"

if __name__ == "__main__":
    test_log_endpoint_returns_success()
    print("PASS: test_log_endpoint_returns_success")
    test_vision_log_endpoint_returns_success()
    print("PASS: test_vision_log_endpoint_returns_success")
    print("All tests PASS")
