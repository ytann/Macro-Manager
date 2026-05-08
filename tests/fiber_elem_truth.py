import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_fiber_key_source_of_truth():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    with patch('litellm.acompletion', new_callable=AsyncMock) as mock_llm:
        # Simulate a response with 'fiber' in a nested structure (simulating inconsistency)
        mock_llm.return_value.choices = [AsyncMock(message=AsyncMock(content='{"calories":100, "macros":{"fiber":5}}'))]
        
        result = await fb.find_source_of_truth("Apple", html_content="<html></html>")
        
        if result and 'fiber' in result:
            print("✅ PASS: 'fiber' is a top-level key in SoT result.")
        else:
            print(f"❌ FAIL: 'fiber' missing or nested in SoT result: {result}")

if __name__ == "__main__":
    asyncio.run(test_fiber_key_source_of_truth())
