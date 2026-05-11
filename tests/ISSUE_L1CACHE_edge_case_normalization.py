import pytest
from unittest.mock import AsyncMock, patch
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService

@pytest.mark.asyncio
async def test_cache_normalization():
    db = DatabaseManager()
    service = FoodbankService(db)
    
    food_name = " Apple "
    mock_data = {"calories": 52, "protein": 0.3, "carbs": 14, "fat": 0.2, "fiber": 2.4}
    
    with patch.object(FoodbankService, '_get_nutrition_data_core', new_callable=AsyncMock) as mock_core:
        mock_core.return_value = mock_data
        
        # Call with spaces and mixed case
        await service.get_nutrition_data(" Apple ")
        await service.get_nutrition_data("apple")
        await service.get_nutrition_data("APPLE")
        
        assert mock_core.call_count == 1
