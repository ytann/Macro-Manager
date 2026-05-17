import pytest
from unittest.mock import MagicMock, patch
import json
from app.services.extraction import ExtractionService
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

@pytest.fixture
def service():
    db = DatabaseManager()
    fb = FoodbankService(db)
    return ExtractionService(fb)

    @pytest.mark.asyncio
    async def test_volumetric_calculation_accuracy(service):
        # Test Case: Medium Bowl (500ml), 60% Cooked Rice (0.75 g/ml)
        # Expected: (500 * 0.6) * 0.75 = 225g
        item_name = "cooked rice"
        fill_pct = 60.0
        utensil_vol = 500.0
    
        grams = service._calculate_mass(item_name, fill_pct, utensil_vol)
        assert grams == 225.0

    @pytest.mark.asyncio
    async def test_volumetric_calculation_fallback(service):
        # Test Case: Unknown food (should use default density 0.8)
        # 500ml, 10% unknown = (500 * 0.1) * 0.8 = 40g
        grams = service._calculate_mass("mystery food", 10.0, 500.0)
        assert grams == 40.0

@pytest.mark.asyncio
async def test_utensil_volume_fallback(service):
    # Test known utensil from config
    assert service._get_utensil_volume("medium_bowl") == 500.0
    # Test unknown utensil -> default
    assert service._get_utensil_volume("weird_container") == 500.0

@pytest.mark.asyncio
async def test_extract_from_image_integration(service):
    # Mock the LLM response to return volumetric JSON
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps({
        "utensil": "medium_bowl",
        "items": [
            {"name": "cooked rice", "fill_percentage": 60.0},
            {"name": "dal", "fill_percentage": 30.0}
        ],
        "reasoning": "Bowl is 500ml. Rice 60%, Dal 30%. Total 90%."
    })
    
    with patch("app.services.extraction.safe_acompletion", return_value=mock_resp):
        # We mock the image and a dummy environment
        log = await service.extract_from_image("dummy_base64", "home")
        
        # Check if grams were calculated correctly
        # Rice: (500 * 0.6) * 0.75 = 225
        # Dal: (500 * 0.3) * 1.1 = 165
        
        # Find the items in the log (they might be expanded into recipes, but for simple items they stay)
        item_names = [it.name for it in log.items]
        assert any("cooked rice" in n for n in item_names)
        assert any("dal" in n for n in item_names)
        
        # Verify the grams for the first item (Rice)
        rice_item = next(it for it in log.items if "cooked rice" in it.name)
        assert rice_item.grams == 225.0
