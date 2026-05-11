import pytest
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService
import asyncio

@pytest.mark.asyncio
async def test_cache_population():
    db = DatabaseManager()
    service = FoodbankService(db)
    
    food_name = "Apple"
    result = await service.get_nutrition_data(food_name)
    
    assert result is not None
    assert "apple" in service._l1_cache
    assert service._l1_cache["apple"] == result
