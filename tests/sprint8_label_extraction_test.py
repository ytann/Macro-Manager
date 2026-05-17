import pytest
from unittest.mock import patch
from app.services.extraction import ExtractionService
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

@pytest.fixture
def db():
    db = DatabaseManager()
    db.foodbank_path = ":memory:"
    db.macros_path = ":memory:"
    db._init_db()
    return db

@pytest.fixture
def extraction(db):
    foodbank = FoodbankService(db)
    return ExtractionService(foodbank)

@pytest.mark.asyncio
async def test_label_extraction(extraction):
    # Mock LiteLLM response for label extraction
    class MockMessage:
        content = '{"product_name": "Test Snack", "reported_qty": 50.0, "protein": 5.0, "carbs": 20.0, "fat": 2.0, "confidence": 95}'
    class MockChoice:
        message = MockMessage()
    class MockResponse:
        choices = [MockChoice()]
        
    with patch('app.services.extraction.safe_acompletion', return_value=MockResponse()):
        # Mock the normalize_and_upsert since we already tested it
        with patch.object(extraction.foodbank, 'normalize_and_upsert') as mock_upsert:
            mock_upsert.return_value = True
            
            # The base64 string is minimal
            b64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP/"
            log = await extraction.extract_from_label(b64, hint="Snack")
            
            # Verify the mock was called with correct extracted data
            mock_upsert.assert_called_once_with(
                name="Test Snack",
                reported_qty=50.0,
                protein=5.0,
                carbs=20.0,
                fat=2.0,
                source="label_scan",
                verified=1
            )
            
            # Verify log creation
            assert len(log.items) == 1
            assert log.items[0].name == "Test Snack"
            assert log.items[0].grams == 50.0
