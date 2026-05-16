import asyncio
from app.core.config import Config
import litellm

# Global semaphore to prevent Ollama saturation across all services
llm_semaphore = asyncio.Semaphore(2)

async def safe_acompletion(*args, **kwargs):
    """Wrapper for litellm.acompletion that respects the global concurrency limit and timeout."""
    async with llm_semaphore:
        return await asyncio.wait_for(litellm.acompletion(*args, **kwargs), timeout=Config.LLM_TIMEOUT)
