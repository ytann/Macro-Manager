import asyncio
import httpx
import json
import os
from typing import List, Tuple

API_URL = "http://localhost:8000"

# TEST CASES: (Query, Expected Path)
TEST_CASES = [
    # --- FAST PATH CASES ---
    ("Hello!", "fast"),
    ("Who are you?", "fast"),
    ("What is MacroManager?", "fast"),
    ("Hi there", "fast"),
    ("Can you hear me?", "fast"),
    ("I'm feeling happy today", "fast"),
    ("Who made you?", "fast"),
    ("Are you a doctor?", "fast"),
    ("Good morning!", "fast"),
    ("Tell me a joke", "fast"),
    ("Thanks for the help!", "fast"),
    ("Are you running locally?", "fast"),
    ("Do you use the internet?", "fast"),
    ("Bye!", "fast"),
    ("What is your name?", "fast"),
    ("How are you doing?", "fast"),
    ("Are you an AI?", "fast"),
    ("Can you help me with my day?", "fast"),
    ("What can you do?", "fast"),
    ("Just checking in", "fast"),
    
    # --- CLINICAL PATH CASES (Must NEVER be fast) ---
    ("What should I eat for lunch?", "clinical"),
    ("I have PMOS, why is my insulin high?", "clinical"),
    ("Can I eat white rice?", "clinical"),
    ("What is the best macro split for me?", "clinical"),
    ("I have sharp abdominal pain, what do I eat?", "clinical"),
    ("Suggest a dinner with salmon", "clinical"),
    ("Explain VPF sequencing", "clinical"),
    ("How does fiber help PMOS?", "clinical"),
    ("Can I eat brown rice instead of white?", "clinical"),
    ("Why should I avoid sugar in the evening?", "clinical"),
    ("What is the difference between soluble and insoluble fiber?", "clinical"),
    ("How does protein affect my insulin?", "clinical"),
    ("Is cinnamon good for PMOS insulin resistance?", "clinical"),
    ("I'm craving chocolate, how can I fit it in?", "clinical"),
    ("What are the best vegetables for PMOS?", "clinical"),
    ("Does eating late at night affect my hormones?", "clinical"),
    ("Should I follow a keto diet for PMOS?", "clinical"),
    ("Can you suggest a high-protein breakfast?", "clinical"),
    ("Why is my energy crashing after lunch?", "clinical"),
    ("Is intermittent fasting good for PCOD?", "clinical"),
    ("What are some low-glycemic fruits?", "clinical"),
    ("How do MUFAs help with androgens?", "clinical"),
    ("Can I have a cheat meal on Sunday?", "clinical"),
    ("What happens if I exceed my carb limit today?", "clinical"),
    ("Is whey protein safe for PMOS?", "clinical"),
    ("Why do I have such strong cravings for sweets?", "clinical"),
    ("I have severe acne, what should I change in my diet?", "clinical"),
    ("Can you explain the 'second-meal effect'?", "clinical"),
    ("What is the impact of saturated fat on PMOS?", "clinical"),
    ("How do I use the Cheat Bank?", "clinical"),
    ("I'm feeling very fatigued, any dietary tips?", "clinical"),
]

async def test_router_leak():
    print("====================================================")
    print("🛡️ ROUTER LEAK & PATH VALIDATION RIG")
    print("====================================================")
    
    passed = 0
    failed = 0
    leaks = 0
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for query, expected in TEST_CASES:
            print(f"Testing: {query[:30]}... ", end="")
            try:
                # We use the /planner endpoint
                response = await client.post(f"{API_URL}/planner", json={
                    "user_query": query,
                    "remaining_macros": {"p": 0, "c": 0, "f": 0, "cal": 0}
                })
                
                if response.status_code != 200:
                    print(f"❌ API Error {response.status_code}")
                    failed += 1
                    continue
                
                # Since the API doesn't return the path, we check the response content.
                # FAST path responses are brief and friendly.
                # CLINICAL path responses are structured (Meal Plan, Clinical Basis, etc.)
                content = response.json().get("suggestion", "").lower()
                
                # HEURISTIC: If it's a clinical query but the response is too short 
                # or doesn't look like a detailed clinical response, it might be a leak.
                # Clinical responses are typically longer and contain clinical terminology.
                content_lower = response.json().get("suggestion", "").lower()
                
                is_clinical_response = (
                    len(content_lower) > 100 or 
                    any(word in content_lower for word in ["clinical", "basis", "macros", "meal plan", "recommend", "pmos", "insulin", "strategy"])
                )
                
                if expected == "clinical" and not is_clinical_response:
                    print(f"🚨 LEAK! Clinical query handled by Fast-Path.")
                    leaks += 1
                    failed += 1
                elif expected == "fast" and is_clinical_response:
                    print(f"⚠️ Over-engineered! Fast query handled by Clinical-Path.")
                    # This is a latency hit, but not a safety failure.
                    passed += 1 
                else:
                    print("✅ Correct Path")
                    passed += 1
                    
            except Exception as e:
                print(f"⚠️ Exception: {e}")
                failed += 1

    print("\n====================================================")
    print(f"FINAL REPORT: {passed}/{len(TEST_CASES)} Passed")
    print(f"CRITICAL LEAKS: {leaks}")
    print("====================================================")
    
    if leaks > 0:
        print("\n🚨 FAILURE: Clinical queries leaked into Fast-Path. The app is UNSAFE.")
        return False
    return True

if __name__ == "__main__":
    asyncio.run(test_router_leak())
