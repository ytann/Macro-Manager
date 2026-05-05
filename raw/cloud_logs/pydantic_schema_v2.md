```python
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class Macros(BaseModel):
    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams")
    fat: float = Field(..., ge=0, description="Fat in grams")

class SubMacros(BaseModel):
    fiber: Optional[float] = Field(None, ge=0)
    sugar: Optional[float] = Field(None, ge=0)
    saturated_fat: Optional[float] = Field(None, ge=0)
    unsaturated_fat: Optional[float] = Field(None, ge=0)
    is_complete_protein: Optional[bool] = None

class FoodItem(BaseModel):
    name: str
    grams: float = Field(..., ge=0)
    cals: float = Field(..., ge=0)
    macros: Macros
    sub_macros: Optional[SubMacros] = None

class FoodLog(BaseModel):
    meal_id: str
    items: List[FoodItem]
    confidence_score: float = Field(..., ge=0, le=1)

    @field_validator('confidence_score')
    @classmethod
    def validate_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Score must be between 0 and 1')
        return v
```

**Reasoning:**
- **Pydantic V2**: Uses `Field` and `field_validator` for strict validation.
- **Strict Macros**: `Macros` model ensures protein, carbs, and fat are always present.
- **Optional Sub-macros**: `SubMacros` allows missing values without failing validation.
- **Constraints**: `ge=0` prevents negative nutritional values; `confidence_score` clamped to [0, 1].
- **Flexibility**: `FoodLog` handles multiple items per meal to accommodate messy input parsing.
