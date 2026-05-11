import pytest
from unittest.mock import AsyncMock, patch
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService

@pytest.mark.asyncio
async def test_cache_hit_prevents_core_call():
    db = DatabaseManager()
    service = FoodbankService(db)
    
    food_name = "Apple"
    mock_data = {"calories": 52, "protein": 0.3, "carbs": 14, "fat": 0.2, "fiber": 2.4}
    
    with patch.object(FoodbankService, '_get_nutrition_data_core', new_callable=AsyncMock) as mock_core:
        mock_core.return_value = mock_data
        
        # First call - should call core
        res1 = await service.get_nutrition_data(food_name)
        # Second call - should hit cache
        res2 = await service.get_nutrition_data(food_name)
        
        assert res1 == mock_data
        assert res2 == mock_data
        assert mock_core.call_count == 1
