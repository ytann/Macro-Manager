import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """
    Centralized configuration for MacroManager.
    """
    # API Config
    LITELLM_API_BASE = "http://localhost:11434"
    LLM_MODEL = 'ollama/gemma4:e2b'
    LLM_TIMEOUT = 60
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    
    # Database Config
    FOODBANK_DB_PATH = "foodbank.db"
    MACROS_DB_PATH = "macros.db"
    
    # App Config
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    
    # Prompt Config
    PROMPTS_PATH = "prompts/prompts.yaml"

class ClinicalConstants:
    """
    Clinically validated constants for PMOS nutritional management.
    """
    # 15% metabolic reduction to account for insulin resistance / mitochondrial dysfunction
    # Citation: general PMOS metabolic adaptation baseline
    PMOS_METABOLIC_PENALTY = 0.85

    # Macro split: 40% Carbs, 35% Protein, 25% Fat
    # Citation: Wycherley RCT (n=43) & meta-analysis on high-protein/low-GI for PMOS
    PMOS_MACRO_SPLIT = {
        "CHO": 0.40,
        "PRO": 0.35,
        "FAT": 0.25
    }

    # Safety guards for daily caloric intake (Adult females)
    MIN_DAILY_CALORIES = 1200
    MAX_DAILY_CALORIES = 4000

    # Standard Utensil Fallbacks (Volumes in ml / cm^3)
    STANDARD_UTENSILS = {
        "small_bowl": 250,
        "medium_bowl": 500,
        "large_bowl": 750,
        "small_plate": 400,
        "medium_plate": 600,
        "large_plate": 1000,
        "teacup": 150,
        "mug": 350,
        "glass": 300,
        "default": 500
    }


