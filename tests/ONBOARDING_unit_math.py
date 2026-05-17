import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.onboarding import OnboardingService

@pytest.mark.asyncio
async def test_onboarding_math_maintain():
    # Mock LLM response
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content='{"age": 30, "height_cm": 160, "weight_kg": 60, "activity_level": 1.2, "goal": "maintain"}'))
    ]

    with patch('litellm.acompletion', return_value=mock_response):
        service = OnboardingService()
        # We don't care about the text since we mock the response
        result = await service.calculate_pmos_baseline("some bio text")

    # Correct Math:
    # BMR = (10*60) + (6.25*160) - (5*30) - 161 = 600 + 1000 - 150 - 161 = 1289
    # TDEE = 1289 * 1.2 = 1546.8
    # Target = round(1546.8 * 0.85) = 1315
    # P = round(1315 * 0.4 / 4) = 132
    # F = round(1315 * 0.35 / 9) = 51
    # C = round(1315 * 0.25 / 4) = 82
    
    assert result["calories"] == 1315.0
    assert result["protein"] == 132.0
    assert result["fat"] == 51.0
    assert result["carbs"] == 82.0

@pytest.mark.asyncio
async def test_onboarding_math_lose():
    # Mock LLM response
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content='{"age": 30, "height_cm": 160, "weight_kg": 60, "activity_level": 1.2, "goal": "lose"}'))
    ]

    with patch('litellm.acompletion', return_value=mock_response):
        service = OnboardingService()
        result = await service.calculate_pmos_baseline("some bio text")
    
    # BMR = 1289
    # TDEE = 1546.8
    # Adjusted TDEE = 1546.8 - 500 = 1046.8
    # Target = round(1046.8 * 0.85) = round(889.78) = 890
    # P = round(890 * 0.4 / 4) = 89
    # F = round(890 * 0.35 / 9) = 35
    # C = round(890 * 0.25 / 4) = 56
    
    assert result["calories"] == 890.0
    assert result["protein"] == 89.0
    assert result["fat"] == 35.0
    assert result["carbs"] == 56.0

if __name__ == "__main__":
    asyncio.run(test_onboarding_math_maintain())
    asyncio.run(test_onboarding_math_lose())
    print("All onboarding tests passed!")
