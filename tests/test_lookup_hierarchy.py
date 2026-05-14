
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService
from app.core.config import Config

@pytest.mark.asyncio
async def test_nutrition_lookup_hierarchy():
    db_manager = DatabaseManager()
    service = FoodbankService(db_manager)
    test_food = "HierarchyFood"
    
    # 1. Mock Data
    db_data = {'name': test_food, 'verified': 0, 'calories': 100.0}
    verified_db_data = {'name': test_food, 'verified': 1, 'calories': 200.0}
    cache_data = {'name': test_food, 'verified': 1, 'calories': 300.0}
    
    # 2. Test Case 1: Item in Cache (Highest Priority)
    service._l1_cache[test_food.lower()] = cache_data
    with patch.object(FoodbankService, 'search_food', new_callable=AsyncMock) as mock_search:
        result = await service.get_nutrition_data(test_food)
        assert result['calories'] == 300.0
        mock_search.assert_not_called()
    
    # Clear cache for next test
    service._l1_cache.clear()
    
    # 3. Test Case 2: Item in DB and Verified (Trust and Return)
    def _insert_verified():
        conn = db_manager.get_foodbank_conn()
        conn.execute(
            "INSERT OR REPLACE INTO foods (name, aliases, calories, protein, carbs, fat, fiber, sugar, saturated_fat, unsaturated_fat, is_complete_protein, verified, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (test_food, test_food.lower(), 200.0, 10.0, 10.0, 10.0, 2.0, 0.0, 0.0, 0.0, 0, 1, "manual_test")
        )
        conn.commit()
    
    await asyncio.to_thread(_insert_verified)
    
    with patch.object(FoodbankService, 'find_source_of_truth', new_callable=AsyncMock) as mock_truth:
        result = await service.get_nutrition_data(test_food)
        assert result['calories'] == 200.0
        mock_truth.assert_not_called()
        
    # 4. Test Case 3: Item in DB but UNVERIFIED (Must search)
    def _insert_unverified():
        conn = db_manager.get_foodbank_conn()
        conn.execute("DELETE FROM foods WHERE name = ?", (test_food,))
        conn.execute(
            "INSERT OR REPLACE INTO foods (name, aliases, calories, protein, carbs, fat, fiber, sugar, saturated_fat, unsaturated_fat, is_complete_protein, verified, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (test_food, test_food.lower(), 100.0, 10.0, 10.0, 10.0, 2.0, 0.0, 0.0, 0.0, 0, 0, "manual_test")
        )
        conn.commit()
        
    await asyncio.to_thread(_insert_unverified)
    service._l1_cache.clear()
    
    with patch.object(FoodbankService, '_is_network_available', new_callable=AsyncMock) as mock_net, \
         patch.object(FoodbankService, 'search_web_for_food', new_callable=AsyncMock) as mock_web:
        
        mock_net.return_value = True
        mock_web.return_value = {'calories': 150.0, 'protein': 10.0, 'carbs': 10.0, 'fat': 10.0, 'fiber': 2.0}
        
        with patch.object(FoodbankService, 'find_source_of_truth', new_callable=AsyncMock) as mock_truth:
            mock_truth.return_value = None
            result = await service.get_nutrition_data(test_food)
            assert result['calories'] == 150.0
            mock_web.assert_called()

if __name__ == "__main__":
    asyncio.run(test_nutrition_lookup_hierarchy())
