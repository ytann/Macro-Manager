import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.onboarding import OnboardingService

@pytest.mark.asyncio
async def test_onboarding_math_maintain():
    # Mock LLM response
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content='{"height_cm": 160, "weight_kg": 60, "activity_level": 1.2, "goal": "maintain"}'))
    ]
    
    with patch('litellm.acompletion', return_value=mock_response):
        service = OnboardingService()
        # We don't care about the text since we mock the response
        result = await service.calculate_pcos_baseline("some bio text")
        
        # Expected: 
        # BMR = (10*60) + (6.25*160) - 125 - 161 = 1314
        # TDEE = 1314 * 1.2 = 1576.8
        # Target = round(1576.8 * 0.85) = 1340
        # P = round(1340 * 0.4 / 4) = 134
        # F = round(1340 * 0.35 / 9) = 52
        # C = round(1340 * 0.25 / 4) = 84
        
        assert result["calories"] == 1340.0
        assert result["protein"] == 134.0
        assert result["fat"] == 52.0
        assert result["carbs"] == 84.0

@pytest.mark.asyncio
async def test_onboarding_math_lose():
    # Mock LLM response
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content='{"height_cm": 160, "weight_kg": 60, "activity_level": 1.2, "goal": "lose"}'))
    ]
    
    with patch('litellm.acompletion', return_value=mock_response):
        service = OnboardingService()
        result = await service.calculate_pcos_baseline("some bio text")
        
        # BMR = 1314
        # TDEE = 1576.8
        # Adjusted TDEE = 1576.8 - 500 = 1076.8
        # Target = round(1076.8 * 0.85) = round(915.28) = 915
        # P = round(915 * 0.4 / 4) = 92
        # F = round(915 * 0.35 / 9) = 36
        # C = round(915 * 0.25 / 4) = 57
        
        assert result["calories"] == 915.0
        assert result["protein"] == 92.0
        assert result["fat"] == 36.0
        assert result["carbs"] == 57.0

if __name__ == "__main__":
    asyncio.run(test_onboarding_math_maintain())
    asyncio.run(test_onboarding_math_lose())
    print("All onboarding tests passed!")
