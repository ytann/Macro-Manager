
import asyncio
import os
import pytest
from unittest.mock import AsyncMock, patch
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService
from app.core.config import Config

@pytest.mark.asyncio
async def test_verification_flow():
    # 1. Setup
    db_manager = DatabaseManager()
    # Ensure we start with a clean state for the test item
    test_food = "TestFood_Unique"
    
    # Manually insert an unverified item
    def _insert_unverified():
        conn = db_manager.get_foodbank_conn()
        # Cleanup just in case
        conn.execute("DELETE FROM foods WHERE name = ?", (test_food,))
        # Using a simplified insert for testing purposes, following the schema
        conn.execute(
            "INSERT OR REPLACE INTO foods (name, aliases, calories, protein, carbs, fat, fiber, sugar, saturated_fat, unsaturated_fat, is_complete_protein, verified, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (test_food, test_food.lower(), 100.0, 10.0, 10.0, 10.0, 2.0, 0.0, 0.0, 0.0, 0, 0, "manual_test")
        )
        conn.commit()
    
    await asyncio.to_thread(_insert_unverified)
    
    service = FoodbankService(db_manager)
    
    # 2. Mock network and web search to simulate successful verification
    mock_web_data = {
        'calories': 110.0,
        'protein': 11.0,
        'carbs': 11.0,
        'fat': 11.0,
        'fiber': 2.2,
        'sugar': 0.5,
        'saturated_fat': 0.1,
        'unsaturated_fat': 0.1
    }
    with patch.object(FoodbankService, '_is_network_available', new_callable=AsyncMock) as mock_net, \
         patch.object(FoodbankService, 'find_source_of_truth', new_callable=AsyncMock) as mock_truth, \
         patch.object(FoodbankService, 'search_web_for_food', new_callable=AsyncMock) as mock_web:
        
        mock_net.return_value = True
        mock_truth.return_value = None # Fail truth search to hit web search
        mock_web.return_value = mock_web_data

        
        # 3. Action: Get nutrition data
        # This should trigger the "not verified -> search -> upsert verified=1" flow
        result = await service.get_nutrition_data(test_food)
        
        # 4. Verification
        assert result is not None
        assert result['calories'] == 110.0
        
        # Check if it was updated to verified = 1 in DB
        def _check_db():
            conn = db_manager.get_foodbank_conn()
            row = conn.execute("SELECT verified FROM foods WHERE name = ?", (test_food,)).fetchone()
            return row['verified'] if row else None
            
        verified_status = await asyncio.to_thread(_check_db)
        assert verified_status == 1, f"Expected verified=1, got {verified_status}"
        
        # Verify that the web search was actually called
        mock_web.assert_called()

if __name__ == "__main__":
    asyncio.run(test_verification_flow())
