import pytest
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager
from app.services.barcode_decoder import BarcodeDecoder

@pytest.fixture
def db():
    # Use an in-memory DB for testing
    db = DatabaseManager()
    # Override paths to memory
    db.foodbank_path = ":memory:"
    db.macros_path = ":memory:"
    db._init_db()
    return db

@pytest.fixture
def foodbank(db):
    service = FoodbankService(db)
    return service

@pytest.mark.asyncio
async def test_normalize_and_upsert(foodbank, db):
    # Test normalization math
    # 250g reported, 12g protein, 50g carbs, 10g fat
    # Expected per 100g: 4.8g protein, 20g carbs, 4g fat
    success = await foodbank.normalize_and_upsert(
        name="Test Cookies",
        reported_qty=250.0,
        protein=12.0,
        carbs=50.0,
        fat=10.0,
        source="label_scan"
    )
    
    assert success is True
    
    # Verify in DB
    conn = db.get_foodbank_conn()
    cursor = conn.execute("SELECT reported_qty, reported_p, p_per_100, verified FROM foods WHERE name = 'Test Cookies'")
    row = cursor.fetchone()
    
    assert row is not None
    assert row['reported_qty'] == 250.0
    assert row['reported_p'] == 12.0
    assert abs(row['p_per_100'] - 4.8) < 0.01
    assert row['verified'] == 1

def test_barcode_decoder_no_library():
    # If pyzbar is not installed in the test environment, it should fail gracefully
    import base64
    # 1x1 pixel black png
    b64 = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82').decode()
    
    result = BarcodeDecoder.decode_from_base64(b64)
    assert result is None
