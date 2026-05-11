import pytest
from app.frontend import render_macro_hud

def test_hud_empty_state():
    consumed = {'protein': 0, 'carbs': 0, 'fat': 0}
    goals = {'protein': 100, 'carbs': 100, 'fat': 100}
    html = render_macro_hud(consumed, goals)
    # Should not have conic-gradient with a percentage > 0
    assert "conic-gradient" not in html or "0%" in html

def test_hud_fill_logic():
    consumed = {'protein': 50, 'carbs': 20, 'fat': 10}
    goals = {'protein': 100, 'carbs': 100, 'fat': 100}
    html = render_macro_hud(consumed, goals)
    # Protein: 50%
    assert "50%" in html
    # Carbs: 20%
    assert "20%" in html
    # Fat: 10%
    assert "10%" in html

def test_hud_protein_alert():
    consumed = {'protein': 120, 'carbs': 50, 'fat': 50}
    goals = {'protein': 100, 'carbs': 100, 'fat': 100}
    html = render_macro_hud(consumed, goals)
    # Protein > 1.0 should have a green exclamation
    # We'll look for a specific class or emoji we plan to use, e.g., 'protein-alert' or '❗'
    assert "protein-alert" in html or "✅" in html or "!" in html

def test_hud_carb_fat_alert():
    consumed = {'protein': 50, 'carbs': 120, 'fat': 120}
    goals = {'protein': 100, 'carbs': 100, 'fat': 100}
    html = render_macro_hud(consumed, goals)
    # Carbs/Fat > 1.0 should have an alert sign
    assert "carb-alert" in html or "fat-alert" in html or "⚠️" in html

def test_hud_clamp_fill():
    consumed = {'protein': 200, 'carbs': 200, 'fat': 200}
    goals = {'protein': 100, 'carbs': 100, 'fat': 100}
    html = render_macro_hud(consumed, goals)
    # Visual fill should be clamped to 100%
    # We check if it doesn't say 200% in the gradient
    assert "200%" not in html
