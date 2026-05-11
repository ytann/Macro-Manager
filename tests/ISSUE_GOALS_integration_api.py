import pytest
from fastapi.testclient import TestClient
from app.api import app
from app.services.database import DatabaseManager

client = TestClient(app)

def test_post_goals_success():
    """Verify that POST /goals successfully updates user goals."""
    payload = {
        "protein": 160.0,
        "carbs": 220.0,
        "fat": 70.0,
        "calories": 2300.0
    }
    response = client.post("/goals", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_goals_reflected_in_summary():
    """Verify that updated goals are reflected in the /summary endpoint."""
    payload = {
        "protein": 170.0,
        "carbs": 230.0,
        "fat": 80.0,
        "calories": 2400.0
    }
    # Update goals
    client.post("/goals", json=payload)
    
    # Fetch summary
    response = client.get("/summary")
    assert response.status_code == 200
    goals = response.json().get("goals", {})
    
    assert goals["protein"] == 170.0
    assert goals["carbs"] == 230.0
    assert goals["fat"] == 80.0
    assert goals["calories"] == 2400.0
