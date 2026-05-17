import asyncio
import base64
import httpx
from app.services.extraction import ExtractionService
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_public_barcode():
    # Coca-Cola barcode: 5449000000996
    # Let's generate a barcode image for this.
    # We can use an online barcode generator API.
    barcode_url = "https://barcode.tec-it.com/barcode.ashx?data=5449000000996&code=EAN13"
    
    print(f"Downloading barcode from {barcode_url}...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(barcode_url)
        if resp.status_code != 200:
            print("Failed to download barcode image.")
            return
        
        b64_image = base64.b64encode(resp.content).decode('utf-8')
        
    print("Initializing services...")
    db = DatabaseManager()
    db.foodbank_path = ":memory:"
    db.macros_path = ":memory:"
    db._init_db()
    
    foodbank = FoodbankService(db)
    extraction = ExtractionService(foodbank)
    
    print("Testing extract_from_qr...")
    try:
        log = await extraction.extract_from_qr(b64_image, hint="")
        print(f"\n✅ SUCCESS! Meal Logged: {log.meal_id}")
        for item in log.items:
            print(f"Item: {item.name}")
            print(f"Grams: {item.grams}")
            print(f"Calories: {item.cals}")
            print(f"Protein: {item.macros.protein}")
            print(f"Carbs: {item.macros.carbs}")
            print(f"Fat: {item.macros.fat}")
            
    except Exception as e:
        print(f"\n❌ FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_public_barcode())
