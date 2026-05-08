import sys
import os
import yaml
sys.path.append(os.getcwd())
from app.core.config import Config

def test_yaml_has_sot_prompt():
    with open(Config.PROMPTS_PATH, 'r') as f:
        prompts = yaml.safe_load(f)
    
    if 'foodbank' in prompts and 'source_of_truth' in prompts['foodbank']:
        print("✅ PASS: 'source_of_truth' prompt found in prompts.yaml.")
    else:
        print("❌ FAIL: 'source_of_truth' prompt missing from prompts.yaml.")

if __name__ == "__main__":
    test_yaml_has_sot_prompt()
