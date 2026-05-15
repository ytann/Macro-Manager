import yaml
from app.core.config import Config

def test_extraction_main_rules():
    with open(Config.PROMPTS_PATH, 'r') as f:
        prompts = yaml.safe_load(f)
    
    main_prompt = prompts.get('extraction', {}).get('main', '')
    
    # Check for CRITICAL CONTEXT PRESERVATION rule
    assert "CRITICAL CONTEXT PRESERVATION" in main_prompt, "FAIL: 'CRITICAL CONTEXT PRESERVATION' rule missing from extraction.main"
    assert "MUST NEVER strip brand names" in main_prompt, "FAIL: 'MUST NEVER strip brand names' instruction missing"
    assert "McDonalds Veg Burger" in main_prompt, "FAIL: Example 'McDonalds Veg Burger' missing"
    assert "Air Fried Chicken Breast" in main_prompt, "FAIL: Example 'Air Fried Chicken Breast' missing"

def test_vision_estimate_rules():
    with open(Config.PROMPTS_PATH, 'r') as f:
        prompts = yaml.safe_load(f)
    
    vision_prompt = prompts.get('extraction', {}).get('vision_estimate', '')
    
    # Check for CRITICAL CONTEXT PRESERVATION rule
    assert "CRITICAL CONTEXT PRESERVATION" in vision_prompt, "FAIL: 'CRITICAL CONTEXT PRESERVATION' rule missing from extraction.vision_estimate"
    assert "USER HINT specifies a brand" in vision_prompt, "FAIL: 'USER HINT specifies a brand' instruction missing"
    assert "Dominos" in vision_prompt, "FAIL: Example 'Dominos' missing"

if __name__ == "__main__":
    try:
        test_extraction_main_rules()
        print("PASS: extraction.main rules verified")
        test_vision_estimate_rules()
        print("PASS: extraction.vision_estimate rules verified")
    except AssertionError as e:
        print(f"FAIL: {e}")
        exit(1)
