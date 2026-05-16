from app.core.llm import safe_acompletion
import yaml
import os
from app.core.config import Config
from app.core.logger import logger

class MemoryService:
    def __init__(self):
        self.memory_file = "app/data/personal_glossary.md"
        self.prompts = self._load_prompts()
        self.model = Config.LLM_MODEL

    def _load_prompts(self) -> dict:
        with open(Config.PROMPTS_PATH, 'r') as f:
            return yaml.safe_load(f)

    async def update_memory(self, new_input: str) -> str:
        current_memory = ""
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r') as f:
                current_memory = f.read()

        prompt = self.prompts['memory']['update_glossary'].format(
            current_memory=current_memory, 
            new_input=new_input
        )

        try:
            resp = await safe_acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                api_base=Config.LITELLM_API_BASE,
                temperature=0.0
            )
            updated_memory = resp.choices[0].message.content.strip()
            
            with open(self.memory_file, 'w') as f:
                f.write(updated_memory)
            
            return updated_memory
        except Exception as e:
            logger.error(f"Memory update failed: {e}")
            raise e
