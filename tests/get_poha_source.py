import asyncio
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService

async def main():
    db = DatabaseManager()
    fb = FoodbankService(db)
    source_data = await fb.find_source_of_truth('poha')
    print(source_data)

if __name__ == "__main__":
    asyncio.run(main())
