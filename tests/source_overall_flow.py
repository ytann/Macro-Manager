import asyncio
import sys
import os
import json
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_source_flow():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    test_food = "SourceFlowFood"
    
    # 1. Trigger Source of Truth search
    # We mock the network to provide specific HTML and the LLM to provide a predictable response
    with patch('app.services.foodbank.FoodbankService._fetch_web_page', new_callable=AsyncMock) as mock_fetch, \
         patch('litellm.acompletion', new_callable=AsyncMock) as mock_llm:
        
        mock_fetch.return_value = "<html>Source: https://example.com/nutrition</html>"
        
        # Mock the LLM response format
        mock_llm.return_value.choices = [
            type('obj', (object,), {
                'message': type('obj', (object,), {'content': json.dumps({
                    'calories': 100, 'protein': 10, 'carbs': 20, 'fat': 1, 'fiber': 2,
                    'source': 'https://example.com/nutrition',
                    'confidence': 'High'
                })})
            })
        ]
        
        await fb.find_source_of_truth(test_food)
        
        # 2. Verify in DB
        conn = db.get_foodbank_conn()
        row = conn.execute("SELECT source FROM foods WHERE name = ?", (test_food,)).fetchone()
        conn.close()
        
        if row and row['source']:
            print(f"✅ PASS: Source persisted correctly: {row['source']}")
        else:
            print("❌ FAIL: Source not found in DB after SoT search.")

if __name__ == "__main__":
    # Patch needs to be inside the script if not using a test runner
    from unittest.mock import AsyncMock, patch
    asyncio.run(test_source_flow())
