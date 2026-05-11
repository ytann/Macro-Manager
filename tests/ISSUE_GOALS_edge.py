import pytest
from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)

def test_goals_negative_values():
    """Verify that negative goal values are rejected by the API (Pydantic validation)."""
    payload = {
        "protein": -10.0,
        "carbs": 200.0,
        "fat": 60.0,
        "calories": 2000.0
    }
    response = client.post("/goals", json=payload)
    # Should return 422 Unprocessable Entity due to Pydantic ge=0 constraint
    assert response.status_code == 422

def test_goals_missing_fields():
    """Verify that requests with missing goal fields are rejected."""
    payload = {
        "protein": 150.0,
        # carbs missing
        "fat": 60.0,
        "calories": 2000.0
    }
    response = client.post("/goals", json=payload)
    assert response.status_code == 422

def test_goals_invalid_types():
    """Verify that non-numeric goal values are rejected."""
    payload = {
        "protein": "a lot",
        "carbs": 200.0,
        "fat": 60.0,
        "calories": 2000.0
    }
    response = client.post("/goals", json=payload)
    assert response.status_code == 422
