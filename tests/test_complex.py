import requests
import json
import time
import subprocess
import os
import sys

# Add root directory to path to allow importing from 'app'
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import foodbank

API_URL = "http://127.0.0.1:8000"


def run_test():
    # Seed DB first
    print("Seeding foodbank...")
    foodbank.seed_db()

    # Start API
    print("Starting API...")
    process = subprocess.Popen(["python3", "api.py"])
    time.sleep(5) # Wait for server to start

    try:
        # 1. Test la-log with complex dish
        test_text = "penne alfredo pasta 1 bowl"
        print(f"\nLogging: {test_text}")
        log_resp = requests.post(f"{API_URL}/log", json={"text": test_text})
        print(f"Log Response: {log_resp.status_code} - {log_resp.text}")

        # 2. Check summary
        print("\nFetching Summary...")
        sum_resp = requests.get(f"{API_URL}/summary")
        print(f"Summary Response: {sum_resp.status_code} - {sum_resp.text}")
        
        data = sum_resp.json()
        if data.get('calories', 0) > 0:
            print("\n✅ SUCCESS: Complex dish logged and totals updated!")
        else:
            print("\n❌ FAILURE: Calories are 0. Deconstruction or DB lookup failed.")

    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        process.terminate()
        print("\nAPI stopped.")

if __name__ == "__main__":
    run_test()
