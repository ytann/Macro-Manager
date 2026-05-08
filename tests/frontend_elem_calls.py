import sys
import os
sys.path.append(os.getcwd())

def test_frontend_sync_calls():
    frontend_path = "app/frontend.py"
    if not os.path.exists(frontend_path):
        print(f"❌ FAIL: {frontend_path} not found.")
        return

    with open(frontend_path, 'r') as f:
        content = f.read()
    
    # Look for requests.get, requests.post, etc.
    import re
    calls = re.findall(r'requests\.(get|post|put|delete|patch)', content)
    
    if calls:
        print(f"❌ FAIL: Found {len(calls)} synchronous requests calls in frontend.py.")
    else:
        print("✅ PASS: No synchronous requests calls found.")

if __name__ == "__main__":
    test_frontend_sync_calls()
