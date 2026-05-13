import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.foodbank import FoodbankService


@pytest.mark.asyncio
async def test_foodbank_service_class_has_close_method():
    """RED: FoodbankService class should define a close() method"""
    assert hasattr(FoodbankService, 'close'), \
        "FoodbankService missing close() method - httpx.AsyncClient never closed"


@pytest.mark.asyncio
async def test_foodbank_service_close_calls_aclose():
    """RED: close() should call http_client.aclose()"""
    with patch.object(FoodbankService, '_load_prompts', return_value={}):
        fb = FoodbankService(MagicMock())
        fb.http_client.aclose = AsyncMock()
        await fb.close()
        fb.http_client.aclose.assert_called_once()