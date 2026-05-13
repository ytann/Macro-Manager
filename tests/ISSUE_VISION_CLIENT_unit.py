import pytest
import httpx
import base64
from unittest.mock import MagicMock, patch
from app.utils.vision_client import send_vision_log

def test_send_vision_log_success():
    # Setup
    image_bytes = b"fake_image_data"
    environment = "Home"
    expected_base64 = base64.b64encode(image_bytes).decode('utf-8')
    mock_response_data = {"status": "success", "items": [{"name": "Apple", "calories": 52}]}
    
    with patch("httpx.post") as mock_post:
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response
        
        # Execute
        result = send_vision_log(image_bytes, environment)
        
        # Assertions
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        
        assert args[0] == "http://localhost:8000/vision-log"
        payload = args[1] if len(args) > 1 else kwargs.get("json")
        
        assert payload["image"] == expected_base64
        assert payload["environment"] == environment
        assert result == mock_response_data

def test_send_vision_log_failure():
    image_bytes = b"fake_image_data"
    environment = "Wild"
    
    with patch("httpx.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Error", request=MagicMock(), response=mock_response)
        mock_post.return_value = mock_response
        
        with pytest.raises(httpx.HTTPStatusError):
            send_vision_log(image_bytes, environment)
