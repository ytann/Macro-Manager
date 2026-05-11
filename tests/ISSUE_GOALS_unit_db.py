import pytest
from app.services.database import DatabaseManager
import os

def test_goals_table_exists():
    """Verify that the goals table is created in macros.db."""
    db = DatabaseManager()
    with db.get_macros_conn() as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='goals'")
        assert cursor.fetchone() is not None, "goals table should exist in macros.db"

def test_set_and_get_daily_goals():
    """Verify that set_daily_goals persists data and get_daily_goals retrieves it."""
    db = DatabaseManager()
    test_goals = {
        "protein": 150.0,
        "carbs": 200.0,
        "fat": 60.0,
        "calories": 2140.0
    }
    
    # Action: Set goals
    db.set_daily_goals(
        protein=test_goals["protein"],
        carbs=test_goals["carbs"],
        fat=test_goals["fat"],
        calories=test_goals["calories"]
    )
    
    # Action: Retrieve goals
    retrieved = db.get_daily_goals()
    
    assert retrieved["protein"] == test_goals["protein"]
    assert retrieved["carbs"] == test_goals["carbs"]
    assert retrieved["fat"] == test_goals["fat"]
    assert retrieved["calories"] == test_goals["calories"]

def test_goals_persistence_across_instances():
    """Verify that goals persist across different DatabaseManager instances."""
    db1 = DatabaseManager()
    db1.set_daily_goals(protein=100, carbs=100, fat=100, calories=2000)
    
    db2 = DatabaseManager()
    retrieved = db2.get_daily_goals()
    assert retrieved["protein"] == 100
