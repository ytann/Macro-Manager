import pytest
import yaml


def test_verification_prompt_formats_without_keyerror():
    with open("prompts/prompts.yaml") as f:
        prompts = yaml.safe_load(f)

    template = prompts["extraction"]["verification"]
    result = template.format(text="dummy", found_details="dummy")

    assert isinstance(result, str)
    assert "dummy" in result
    assert "{content}" not in result