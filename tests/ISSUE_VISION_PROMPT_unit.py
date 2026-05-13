import sys
import os
import yaml
sys.path.append(os.getcwd())
from app.core.config import Config

def test_vision_estimate_prompt_exists_and_formats():
    with open(Config.PROMPTS_PATH, 'r') as f:
        prompts = yaml.safe_load(f)

    vision_block = prompts.get('extraction', {}).get('vision_estimate')
    assert vision_block is not None, "FAIL: 'extraction.vision_estimate' key missing from prompts.yaml"

    home_fmt = vision_block.format(environment="Home")
    assert "Home" in home_fmt, "FAIL: formatted prompt does not contain 'Home'"

    wild_fmt = vision_block.format(environment="Wild")
    assert "Wild" in wild_fmt, "FAIL: formatted prompt does not contain 'Wild'"

    assert len(home_fmt.strip()) > 0
    assert len(wild_fmt.strip()) > 0

if __name__ == "__main__":
    test_vision_estimate_prompt_exists_and_formats()
    print("PASS: vision_estimate prompt exists and formats with {environment} kwarg")