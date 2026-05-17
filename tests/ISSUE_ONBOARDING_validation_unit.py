import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch
from app.services.onboarding import OnboardingService, OnboardingValidationError

import json

@pytest.mark.asyncio
async def test_onboarding_validation_fail():
    service = OnboardingService()
    
    # Mock litellm.acompletion to return malformed JSON
    malformed_response = AsyncMock()
    malformed_response.choices = [
        AsyncMock(message=AsyncMock(content=json.dumps({"invalid_key": "value"})))
    ]
    
    with patch('litellm.acompletion', return_value=malformed_response):
        # This should currently pass because of .get() defaults,
        # but it should FAIL with OnboardingValidationError after the fix.
        with pytest.raises(OnboardingValidationError):
            await service.calculate_pmos_baseline("Some bio text")


@pytest.mark.asyncio
async def test_onboarding_validation_success():
    service = OnboardingService()
    
    # Mock litellm.acompletion to return valid JSON
    valid_response = AsyncMock()
    valid_response.choices = [
        AsyncMock(message=AsyncMock(content=json.dumps({
            "age": 30,
            "height_cm": 170,
            "weight_kg": 70,
            "activity_level": 1.2,
            "goal": "lose"
        })))
    ]
    
    with patch('litellm.acompletion', return_value=valid_response):
        result = await service.calculate_pmos_baseline("Some bio text")
        assert "calories" in result
        assert "protein" in result
