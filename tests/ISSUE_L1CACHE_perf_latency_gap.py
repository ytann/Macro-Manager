import pytest
import asyncio
import time
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService

@pytest.mark.asyncio
async def test_latency_gap():
    db = DatabaseManager()
    service = FoodbankService(db)
    
    # Case 1: Verified Item (Rice is in seed DB)
    verified_food = "Rice"
    
    start_t1 = time.perf_counter()
    await service.get_nutrition_data(verified_food)
    t1_verified = time.perf_counter() - start_t1
    
    start_t2 = time.perf_counter()
    await service.get_nutrition_data(verified_food)
    t2_verified = time.perf_counter() - start_t2
    
    # Case 2: New Common Item (Avocado - not in seed DB)
    new_food = "Avocado"
    
    start_t3 = time.perf_counter()
    await service.get_nutrition_data(new_food)
    t3_new = time.perf_counter() - start_t3
    
    start_t4 = time.perf_counter()
    await service.get_nutrition_data(new_food)
    t4_new = time.perf_counter() - start_t4
    
    print(f"\n--- L1 Cache Performance Report ---")
    print(f"Verified Item ({verified_food}):")
    print(f"  First call (DB): {t1_verified:.6f}s")
    print(f"  Second call (L1): {t2_verified:.6f}s")
    print(f"  Gap: {t1_verified - t2_verified:.6f}s")
    
    print(f"New Item ({new_food}):")
    print(f"  First call (Web/LLM): {t3_new:.6f}s")
    print(f"  Second call (L1): {t4_new:.6f}s")
    print(f"  Gap: {t3_new - t4_new:.6f}s")
    print(f"----------------------------------\n")
    
    assert t2_verified < t1_verified
    assert t4_new < t3_new
