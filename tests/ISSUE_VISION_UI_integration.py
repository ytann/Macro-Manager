import pytest
from streamlit.testing.v1 import AppTest
from unittest.mock import patch, MagicMock
from app.utils.vision_client import send_vision_log

def test_vision_ui_integration():
    """
    Test that the 'Snap Meal' UI correctly calls send_vision_log when an image is provided.
    """
    at = AppTest.from_file("app/frontend.py").run()
    
    # 1. Find the radio toggle for environment
    # Streamlit AppTest allows interacting with widgets.
    # We need to identify the radio widget.
    radio = at.radio[0] # Assuming it's the first radio
    radio.set_value("Wild").run()
    
    # 2. Mock send_vision_log
    with patch("app.frontend.send_vision_log") as mock_send:
        mock_send.return_value = {"status": "success", "items": [{"name": "Test Food", "calories": 100}]}
        
        # 3. Simulate camera input
        # AppTest.camera_input is available. 
        # We simulate uploading a file.
        camera = at.camera_input[0]
        camera.upload(b"fake_image_bytes").run()
        
        # 4. Verify send_vision_log was called with correct args
        mock_send.assert_called_once_with(b"fake_image_bytes", "Wild")
        
        # 5. Verify success message is displayed
        assert "Extracted: Test Food (100 kcal)" in at.markdown[0].value or \
               any("Extracted: Test Food (100 kcal)" in str(element) for element in at.get("success"))

if __name__ == "__main__":
    pytest.main([__file__])
