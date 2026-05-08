import sys
import os
sys.path.append(os.getcwd())

def test_frontend_requests_import():
    frontend_path = "app/frontend.py"
    if not os.path.exists(frontend_path):
        print(f"❌ FAIL: {frontend_path} not found.")
        return

    with open(frontend_path, 'r') as f:
        content = f.read()
    
    if "import requests" in content or "from requests import" in content:
        print("❌ FAIL: 'requests' library is imported in frontend.py.")
    else:
        print("✅ PASS: 'requests' library not found in imports.")

if __name__ == "__main__":
    test_frontend_requests_import()
