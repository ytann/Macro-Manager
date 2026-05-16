import httpx
import base64

# Shared client to reuse TCP connections (Connection Pooling)
_client = httpx.Client(timeout=60.0)

def send_vision_log(image_bytes: bytes, environment: str, hint: str = ""):
    """
    Encodes image bytes to base64 and sends it to the vision-log API endpoint.
    """
    url = "http://localhost:8000/vision-log"
    encoded_image = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "base64_image": encoded_image,
        "environment": environment,
        "hint": hint
    }
    
    response = _client.post(url, json=payload)
    response.raise_for_status()
    return response.json()
