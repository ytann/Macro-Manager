import asyncio
import httpx

async def check_summary():
    url = "http://127.0.0.1:8000/summary"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            print(f"Status: {response.status_code}")
            print(f"JSON: {response.json()}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_summary())
