import pytest
import asyncio
from unittest.mock import MagicMock, patch
import sys
import os
sys.path.append(os.getcwd())

from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService

@pytest.mark.asyncio
async def test_seed_db_uses_executemany():
    db = DatabaseManager()
    service = FoodbankService(db)
    
    # Mock the connection
    mock_conn = MagicMock()
    
    # Mock DatabaseManager.get_foodbank_conn to return our mock_conn
    with patch.object(db, 'get_foodbank_conn', return_value=mock_conn):
        await service.seed_db()
        
        # Check if executemany was called on the connection
        mock_conn.executemany.assert_called_once()

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
