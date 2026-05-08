import asyncio
import sys
import os
import yaml
from unittest.mock import AsyncMock, patch
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager
from app.core.config import Config

async def test_prompt_change_reflects():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    # 1. Define a unique prompt string
    unique_marker = "UNIQUE_PROMPT_MARKER_123"
    original_prompts = {}
    with open(Config.PROMPTS_PATH, 'r') as f:
        original_prompts = yaml.safe_load(f)
    
    # 2. Mock the prompt in the service's loaded prompts
    fb.prompts['source_of_truth'] = f"Verify food using {unique_marker}"
    
    # 3. Mock the LLM call to see what prompt was sent
    with patch('litellm.acompletion', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value.choices = [AsyncMock(message=AsyncMock(content='{"calories": 10}'))]
        
        await fb.find_source_of_truth("Apple", html_content="<html></html>")
        
        # Check if the prompt sent to litellm contains the unique marker
        args, kwargs = mock_llm.call_args
        messages = kwargs.get('messages', [])[0].get('content', '')
        
        if unique_marker in messages:
            print("✅ PASS: Prompt changes are reflected in the LLM call.")
        else:
            print("❌ FAIL: LLM call used a different prompt than what was in fb.prompts.")

if __name__ == "__main__":
    asyncio.run(test_prompt_change_reflects())
