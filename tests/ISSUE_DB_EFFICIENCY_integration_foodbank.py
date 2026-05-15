import pytest
import asyncio
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService
from app.core.config import Config
import os
import sqlite3

@pytest.fixture
def db_manager(tmp_path):
    # Use temporary database paths for tests
    foodbank_path = str(tmp_path / "test_foodbank.db")
    macros_path = str(tmp_path / "test_macros.db")
    
    # Patch Config to use temp paths
    Config.FOODBANK_DB_PATH = foodbank_path
    Config.MACROS_DB_PATH = macros_path
    
    return DatabaseManager()

@pytest.fixture
def foodbank_service(db_manager):
    return FoodbankService(db_manager)

@pytest.mark.asyncio
async def test_foodbank_db_operations(foodbank_service):
    # Test upsert_food
    food_name = "Test Food"
    await foodbank_service.upsert_food(
        name=food_name, 
        calories=100, protein=10, carbs=10, fat=5, fiber=2, 
        sugar=1, sat_fat=1, unsat_fat=1, verified=1, source="test"
    )
    
    # Test search_food
    result = await foodbank_service.search_food(food_name)
    assert result is not None
    assert result['name'] == food_name
    assert result['calories'] == 100
    
    # Test queue_for_verification
    verify_name = "Verify Me"
    await foodbank_service.queue_for_verification(verify_name)
    count = await foodbank_service.get_pending_count()
    assert count >= 1
    
    # Test update_sync_timestamp
    await foodbank_service.update_sync_timestamp()
    ts = await foodbank_service.get_sync_timestamp()
    assert ts is not None

    # Test get_recipe / save_recipe
    recipe_name = "Test Recipe"
    recipe_data = [{"name": "Item 1", "grams": 100}, {"name": "Item 2", "grams": 200}]
    await foodbank_service.save_recipe(recipe_name, recipe_data)
    retrieved_recipe = await foodbank_service.get_recipe(recipe_name)
    assert retrieved_recipe == recipe_data

    await foodbank_service.close()
