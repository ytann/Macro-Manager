import os

class Config:
    """
    Centralized configuration for MacroManager.
    """
    # API Config
    LITELLM_API_BASE = "http://localhost:11434"
    LLM_MODEL = 'ollama/gemma4:e2b'
    
    # Database Config
    FOODBANK_DB_PATH = "foodbank.db"
    MACROS_DB_PATH = "macros.db"
    
    # App Config
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    
    # Prompt Config
    PROMPTS_PATH = "prompts/prompts.yaml"
