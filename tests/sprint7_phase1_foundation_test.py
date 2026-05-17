import json
import os
from app.core.config import ClinicalConstants

def test_densities_json_structure():
    path = "app/core/densities.json"
    assert os.path.exists(path), "densities.json should exist"
    
    with open(path, 'r') as f:
        data = json.load(f)
    
    assert "categories" in data, "JSON must contain 'categories'"
    assert "specific" in data, "JSON must contain 'specific'"
    assert "fallbacks" in data, "JSON must contain 'fallbacks'"
    assert data["fallbacks"]["default_density"] == 0.8

def test_standard_utensils_config():
    assert hasattr(ClinicalConstants, "STANDARD_UTENSILS"), "ClinicalConstants should have STANDARD_UTENSILS"
    assert ClinicalConstants.STANDARD_UTENSILS["medium_bowl"] == 500
    assert ClinicalConstants.STANDARD_UTENSILS["default"] == 500

def test_volumetric_math_simulation():
    """
    Simulate the proposed physics: Mass = (Total Vol * Fill%) * Density
    Example: 500ml bowl, 60% rice (0.75 g/ml)
    Mass = (500 * 0.6) * 0.75 = 300 * 0.75 = 225g
    """
    total_vol = 500
    fill_pct = 0.6
    density = 0.75
    
    calculated_mass = (total_vol * fill_pct) * density
    assert calculated_mass == 225.0

def test_edge_case_zero_volume():
    total_vol = 0
    fill_pct = 0.5
    density = 1.0
    assert (total_vol * fill_pct) * density == 0

def test_edge_case_full_volume():
    total_vol = 500
    fill_pct = 1.0
    density = 1.0
    assert (total_vol * fill_pct) * density == 500
