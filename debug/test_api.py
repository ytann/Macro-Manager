import subprocess
import time
import requests
import os

# Set PYTHONPATH
os.environ['PYTHONPATH'] = os.getcwd()

def test():
    print("Starting API...")
    process = subprocess.Popen(['python3', 'app/api.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(5)
    
    try:
        print("Testing /log...")
        resp = requests.post("http://127.0.0.1:8000/log", json={"text": "2 eggs", "meal_type": "Breakfast"})
        print(f"Log response: {resp.status_code}")
        
        print("Testing /summary...")
        resp = requests.get("http://127.0.0.1:8000/summary")
        print(f"Summary response: {resp.status_code}")
        
        print("Testing /meals...")
        resp = requests.get("http://127.0.0.1:8000/meals")
        print(f"Meals response: {resp.status_code}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        process.terminate()

if __name__ == "__main__":
    test()
