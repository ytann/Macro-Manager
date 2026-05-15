import asyncio
from app.core.config import Config
import litellm

# Global semaphore to prevent Ollama saturation across all services
llm_semaphore = asyncio.Semaphore(2)

async def safe_acompletion(*args, **kwargs):
    """Wrapper for litellm.acompletion that respects the global concurrency limit."""
    async with llm_semaphore:
        return await litellm.acompletion(*args, **kwargs)
