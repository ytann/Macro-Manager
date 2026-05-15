import asyncio
import json
from app.services.extraction import ExtractionService
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def debug_parse(text):
    print(f"\n--- Debugging: '{text}' ---")
    db = DatabaseManager()
    fb = FoodbankService(db)
    service = ExtractionService(fb)
    
    # We want to see the intermediate steps
    # 1. Voice correction
    correction_prompt = service.prompts['extraction']['voice_correction'].format(text=text)
    import litellm
    corr_resp = await litellm.acompletion(
        model=service.model,
        messages=[{"role": "user", "content": correction_prompt}],
        api_base=service.model, # Wait, this should be Config.LITELLM_API_BASE
        temperature=0.0
    )
    # Correction to the above: the service already has the config.
    # Let's just use the service.parse and print logs.
    
async def main():
    # Actually, let's just use the actual parse method and look at the logs.
    # But I need to make sure I use the right API base.
    from app.core.config import Config
    import litellm
    litellm.api_base = Config.LITELLM_API_BASE
    
    db = DatabaseManager()
    fb = FoodbankService(db)
    service = ExtractionService(fb)
    
    text = "1 plate misal pav"
    try:
        print(f"Parsing: {text}")
        result = await service.parse(text)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
