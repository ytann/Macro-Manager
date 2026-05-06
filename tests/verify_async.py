import asyncio
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService
from app.services.extraction import ExtractionService

async def test():
    db = DatabaseManager()
    fb = FoodbankService(db)
    ex = ExtractionService(fb)
    print("Parsing...")
    res = await ex.parse('2 boiled eggs and an apple')
    print(f"Success: {res.total_calories}")

if __name__ == "__main__":
    asyncio.run(test())
