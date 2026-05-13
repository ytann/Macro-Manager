import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.getcwd())

from app.api import app, extraction_service
from app.schemas.food_schemas import FoodItem, Macros, SubMacros

client = TestClient(app)

dummy_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


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
        data = response.json()
        assert data["status"] == "success", f"FAIL: unexpected response: {data}"

        mock_vision.assert_called_once_with(dummy_base64, "Home")


def test_vision_log_endpoint_defaults_environment():
    mock_items = [{"name": "Apple", "grams": 150}]
    mock_result = (
        {"p": 0.5, "c": 20.0, "f": 0.3, "cal": 80.0},
        FoodItem(
            name="Apple", grams=150, cals=80.0,
            macros=Macros(protein=0.5, carbs=20.0, fat=0.3),
            verified=False
        )
    )

    with patch.object(extraction_service, 'extract_from_image', new_callable=AsyncMock) as mock_vision, \
         patch.object(extraction_service, '_get_nutrition_for_ingredient', new_callable=AsyncMock) as mock_nutrition:

        mock_vision.return_value = mock_items
        mock_nutrition.return_value = mock_result

        response = client.post("/vision-log", json={"base64_image": dummy_base64})

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_vision.assert_called_once_with(dummy_base64, "Home")


if __name__ == "__main__":
    test_vision_log_endpoint_returns_success()
    print("PASS: test_vision_log_endpoint_returns_success")
    test_vision_log_endpoint_defaults_environment()
    print("PASS: test_vision_log_endpoint_defaults_environment")
    print("All tests PASS")