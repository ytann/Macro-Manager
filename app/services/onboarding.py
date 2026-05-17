from app.core.llm import safe_acompletion
import json
import yaml
from pydantic import ValidationError
from app.core.config import Config, ClinicalConstants
from app.core.logger import logger
from app.schemas.food_schemas import OnboardingAttributes

class OnboardingValidationError(Exception):
    """Custom exception for onboarding validation failures."""
    def __init__(self, errors: list):
        self.errors = errors
        super().__init__(f"Validation failed with {len(errors)} errors")

class OnboardingService:
    def __init__(self):
        self.prompts = self._load_prompts()
        self.model = Config.LLM_MODEL

    def _load_prompts(self):
        with open(Config.PROMPTS_PATH, 'r') as f:
            return yaml.safe_load(f)

    async def calculate_pmos_baseline(self, text: str) -> dict:
        prompt = self.prompts['extraction']['onboarding_parse'].format(text=text)
        resp = await safe_acompletion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            api_base=Config.LITELLM_API_BASE,
            temperature=0.0
        )
        
        try:
            # Pydantic v2: Use model_validate_json for direct parsing from string
            attrs = OnboardingAttributes.model_validate_json(resp.choices[0].message.content)
        except ValidationError as e:
            logger.error(f"Onboarding extraction failed validation: {e}")
            # Extract a user-friendly list of errors
            error_details = [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
            raise OnboardingValidationError(error_details)
        except Exception as e:
            logger.error(f"Onboarding extraction unexpected error: {e}")
            raise ValueError(f"Failed to parse biometrics: {e}")

        age = attrs.age
        height_cm = attrs.height_cm
        weight_kg = attrs.weight_kg
        activity_level = attrs.activity_level
        goal = attrs.goal.lower()

        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
        tdee = bmr * activity_level

        goal_modifiers = {'lose': -500, 'gain': 500, 'maintain': 0}
        modifier = goal_modifiers.get(goal, 0)
        adjusted_tdee = tdee + modifier

        # Apply clinical metabolic penalty and ensure safety bounds
        target_calories = round(adjusted_tdee * ClinicalConstants.PMOS_METABOLIC_PENALTY)
        target_calories = max(ClinicalConstants.MIN_DAILY_CALORIES, min(target_calories, ClinicalConstants.MAX_DAILY_CALORIES))

        # Macro Split: 40% Carbs, 35% Protein, 25% Fat (Wycherley RCT)
        carbs = round((target_calories * ClinicalConstants.PMOS_MACRO_SPLIT["CHO"]) / 4)
        protein = round((target_calories * ClinicalConstants.PMOS_MACRO_SPLIT["PRO"]) / 4)
        fat = round((target_calories * ClinicalConstants.PMOS_MACRO_SPLIT["FAT"]) / 9)

        logger.info(f"PMOS baseline calculated: cal={target_calories}, p={protein}, c={carbs}, f={fat}")

        return {
            "protein": float(protein),
            "carbs": float(carbs),
            "fat": float(fat),
            "calories": float(target_calories)
        }
