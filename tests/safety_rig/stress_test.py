import asyncio
import httpx
import time
import random
import json
import os
from typing import List

API_URL = "http://localhost:8000"
LOG_FILE = "tests/safety_rig/stress_results.jsonl"

async def send_request(client: httpx.AsyncClient, endpoint: str, payload: dict):
    try:
        start = time.time()
        resp = await client.post(f"{API_URL}{endpoint}", json=payload, timeout=40.0)
        result = {"endpoint": endpoint, "status": resp.status_code, "latency": time.time() - start, "error": None, "response": resp.text[:500]}
        return result
    except Exception as e:
        result = {"endpoint": endpoint, "status": "ERROR", "latency": 0, "error": str(e), "response": None}
        return result

async def run_stress_test():
    print("====================================================")
    print("🌋 MACROMANAGER STRESS & CHAOS RIG")
    print("====================================================")
    
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    
    endpoints = [
        ("/log", {"text": "Apple 100g", "meal_type": "General"}),
        ("/planner", {"user_query": "What should I eat?", "remaining_macros": {"p": 10, "c": 20, "f": 10, "cal": 200}}),
        ("/onboard", {"bio_text": "30yo female, 160cm, 70kg, active, PMOS"}),
        ("/memory", {"text": "I love blueberries"})
    ]
    
    total_requests = 100
    concurrency = 5
    results = []
    
    async with httpx.AsyncClient() as client:
        # PHASE 1: Baseline Load
        print(f"Step 1: Baseline Load ({total_requests} requests)...")
        tasks = []
        for _ in range(total_requests):
            ep, payload = random.choice(endpoints)
            tasks.append(send_request(client, ep, payload))
        
        # Execute in chunks to maintain concurrency
        for i in range(0, len(tasks), concurrency):
            chunk = tasks[i:i+concurrency]
            batch_results = await asyncio.gather(*chunk)
            results.extend(batch_results)
            # Log batch results
            with open(LOG_FILE, "a") as f:
                for res in batch_results:
                    f.write(json.dumps(res) + "\n")
            if i % 20 == 0: print(f"Progress: {i}/{total_requests}...")

        # PHASE 2: THE CHAOS WINDOW
        print("\n" + "!"*60)
        print("⚠️  CHAOS WINDOW OPEN: RESTART OLLAMA NOW! ⚠️")
        print("!"*60)
        
        # We keep firing requests while the user restarts Ollama
        chaos_results = []
        for _ in range(20):
            ep, payload = random.choice(endpoints)
            res = await send_request(client, ep, payload)
            chaos_results.append(res)
            print(f"Chaos request: {res['status']} ({res['latency']:.2f}s)")
            
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(res) + "\n")
                
            await asyncio.sleep(2)
            
        results.extend(chaos_results)
        
        # PHASE 3: Recovery Check
        print("\nStep 3: Recovery Check (Post-Restart)...")
        recovery_results = []
        for _ in range(20):
            ep, payload = random.choice(endpoints)
            res = await send_request(client, ep, payload)
            recovery_results.append(res)
            print(f"Recovery request: {res['status']} ({res['latency']:.2f}s)")
            
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(res) + "\n")
                
            await asyncio.sleep(1)
            
        results.extend(recovery_results)

    # FINAL ANALYSIS
    successes = [r for r in results if r['status'] == 200]
    errors_500 = [r for r in results if r['status'] == 500]
    timeouts = [r for r in results if r['status'] == "ERROR" or r['latency'] > 30]
    
    print("\n====================================================")
    print("STRESS TEST FINAL REPORT")
    print("====================================================")
    print(f"Total Requests: {len(results)}")
    print(f"✅ Successes (200): {len(successes)}")
    print(f"❌ Server Errors (500): {len(errors_500)}")
    print(f"⏱️ Timeouts/Errors: {len(timeouts)}")
    
    if len(errors_500) == 0:
        print("\n🏆 STABILITY VERIFIED: No 500 errors during chaos.")
    else:
        print("\n🚨 STABILITY FAILED: Server crashed or returned 500s.")
    print("====================================================")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
