import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import app.frontend

@pytest.mark.asyncio
async def test_frontend_client_pooling():
    with patch('app.frontend._client') as mock_client:
        # Mock the async methods
        mock_client.get = AsyncMock(return_value=MagicMock(status_code=200))
        mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
        mock_client.delete = AsyncMock(return_value=MagicMock(status_code=200))
        
        # Call each helper
        await app.frontend.async_get("http://test.com")
        await app.frontend.async_post("http://test.com", {})
        await app.frontend.async_delete("http://test.com")

        # Since we patched the module-level _client, it's shared.
        # We just need to verify that the functions are actually calling THIS client.
        assert mock_client.get.called
        assert mock_client.post.called
        assert mock_client.delete.called

if __name__ == "__main__":
    asyncio.run(test_frontend_client_pooling())


