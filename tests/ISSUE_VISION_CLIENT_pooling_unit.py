import pytest
from unittest.mock import patch, MagicMock
from app.utils.vision_client import send_vision_log

import pytest
from unittest.mock import patch, MagicMock
from app.utils.vision_client import send_vision_log

@patch('app.utils.vision_client._client')
def test_send_vision_log_success(mock_client):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_client.post.return_value = mock_response
    
    image_bytes = b"fake image data"
    env = "Home"
    
    result = send_vision_log(image_bytes, env)
    assert result == {"status": "success"}
    mock_client.post.assert_called_once()
