import pytest
import asyncio
from unittest.mock import MagicMock, patch
from app.services.foodbank import FoodbankService

@pytest.mark.asyncio
async def test_foodbank_service_has_close_method():
    # Setup
    mock_db = MagicMock()
    with patch.object(FoodbankService, '_load_prompts', return_value={}):
        service = FoodbankService(mock_db)
    
    # The test should fail if close() doesn't exist
    assert hasattr(service, 'close'), "FoodbankService should have a close() method"
    
    # Verify it actually closes the http_client
    client = service.http_client
    await service.close()
    assert client.is_closed, "httpx.AsyncClient should be closed after service.close() is called"

if __name__ == "__main__":
    asyncio.run(test_foodbank_service_has_close_method())
