import requests
import os
from app.services.database import init_db

API_URL = "http://127.0.0.1:8000"

def reset_db():
    print("Resetting database...")
    if os.path.exists("macros.db"):
        os.remove("macros.db")
    init_db()

def test_logging_and_summary():
    # 1. Test logging a simple item
    print("\nTesting Log: 1 apple")
    log_payload = {"text": "I ate 1 apple"}
    try:
        resp = requests.post(f"{API_URL}/log", json=log_payload)
        print(f"Status: {resp.status_code}, Response: {resp.text}")
        if resp.status_code != 200:
            print("❌ Log failed")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

    # 2. Test summary
    print("\nTesting Summary...")
    try:
        resp = requests.get(f"{API_URL}/summary")
        print(f"Status: {resp.status_code}, Response: {resp.text}")
        data = resp.json()
        if data.get('consumed', {}).get('calories', 0) == 0:
            print("❌ Summary returned 0 calories - Daily totals not updating!")
        else:
            print("✅ Summary returned data")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    # Note: This requires the API to be running in the background
    test_logging_and_summary()
