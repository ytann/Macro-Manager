import asyncio
import json
import os
from app.services.planner import PlannerService

async def test_planner_basic_flow():
    print("Running test_planner_basic_flow...")
    planner = PlannerService()
    
    # Mock data
    user_query = "What should I eat for dinner to manage my PMOS?"
    remaining_macros = {"calories": 500, "protein": 30, "carbs": 40, "fat": 15}
    
    try:
        print("Calling router...")
        # We can't easily call individual steps because they are private in generate_suggestion
        # but we can see if it progresses.
        response = await planner.generate_suggestion(user_query, remaining_macros)
        print(f"Response received: {response[:100]}...")
        
        if "🚨 Copilot Error" in response:
            print("FAIL: Copilot returned an error.")
            return False
        
        if not response or len(response) < 10:
            print("FAIL: Response too short or empty.")
            return False
            
        print("SUCCESS: Basic flow completed.")
        return True
    except Exception as e:
        print(f"FAIL: Exception occurred: {e}")
        return False

async def main():
    success = await test_planner_basic_flow()
    if success:
        print("\nALL TESTS PASSED")
        exit(0)
    else:
        print("\nSOME TESTS FAILED")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
