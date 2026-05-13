import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from app.services.extraction import ExtractionService


@pytest.mark.asyncio
async def test_name_error_when_all_items_are_recipes():
    mock_fb = MagicMock()
    mock_fb.get_recipe = AsyncMock(return_value=[{"name": "ingredient", "grams": 100}])
    mock_fb.get_nutrition_data = AsyncMock(return_value={
        "protein": 10, "carbs": 20, "fat": 5, "calories": 165, "fiber": 2, "verified": False
    })

    service = ExtractionService(mock_fb)

    responses = [
        MagicMock(),  # voice correction
        MagicMock(),  # main extraction
        MagicMock(),  # verification guardrail
    ]
    responses[0].choices = [MagicMock()]
    responses[0].choices[0].message.content = "TestDish 200g"
    responses[1].choices = [MagicMock()]
    responses[1].choices[0].message.content = json.dumps({"items": [{"name": "TestDish", "grams": 200}]})
    responses[2].choices = [MagicMock()]
    responses[2].choices[0].message.content = json.dumps({"missing": []})

    mock_acompletion = AsyncMock(side_effect=responses)

    with patch("app.services.extraction.litellm.acompletion", mock_acompletion):
        result = await service.parse("TestDish 200g", "test_meal")
        assert result is not None
        assert len(result.items) > 0