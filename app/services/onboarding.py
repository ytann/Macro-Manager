import litellm
import json
import yaml
from app.core.config import Config
from app.core.logger import logger


class OnboardingService:
    def __init__(self):
        self.prompts = self._load_prompts()
        litellm.api_base = Config.LITELLM_API_BASE
        self.model = Config.LLM_MODEL

    def _load_prompts(self):
        with open(Config.PROMPTS_PATH, 'r') as f:
            return yaml.safe_load(f)

    async def calculate_pcos_baseline(self, text: str) -> dict:
        prompt = self.prompts['extraction']['onboarding_parse'].format(text=text)
        resp = await litellm.acompletion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            api_base=Config.LITELLM_API_BASE,
            temperature=0.0
        )
        data = json.loads(resp.choices[0].message.content)

        age = int(data.get('age', 25))
        height_cm = int(data.get('height_cm', 160))
        weight_kg = float(data.get('weight_kg', 65))
        activity_level = float(data.get('activity_level', 1.2))
        goal = str(data.get('goal', 'maintain')).lower()

        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
        tdee = bmr * activity_level

        goal_modifiers = {'lose': -500, 'gain': 500, 'maintain': 0}
        modifier = goal_modifiers.get(goal, 0)
        adjusted_tdee = tdee + modifier

        target_calories = round(adjusted_tdee * 0.85)
        protein = round((target_calories * 0.4) / 4)
        fat = round((target_calories * 0.35) / 9)
        carbs = round((target_calories * 0.25) / 4)

        logger.info(f"PCOS baseline calculated: cal={target_calories}, p={protein}, c={carbs}, f={fat}")

        return {
            "protein": float(protein),
            "carbs": float(carbs),
            "fat": float(fat),
            "calories": float(target_calories)
        }