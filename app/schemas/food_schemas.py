from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class Macros(BaseModel):
    protein: float = Field(..., ge=0, le=1000, description="Protein in grams")
    carbs: float = Field(..., ge=0, le=1000, description="Carbohydrates in grams")
    fat: float = Field(..., ge=0, le=1000, description="Fat in grams")

class SubMacros(BaseModel):
    fiber: Optional[float] = Field(None, ge=0)
    sugar: Optional[float] = Field(None, ge=0)
    saturated_fat: Optional[float] = Field(None, ge=0)
    unsaturated_fat: Optional[float] = Field(None, ge=0)
    is_complete_protein: Optional[bool] = None

class FoodItem(BaseModel):
    name: str
    grams: float = Field(..., ge=0, le=10000)
    cals: float = Field(..., ge=0, le=10000)
    macros: Macros
    sub_macros: Optional[SubMacros] = None
    verified: bool = False

class FoodLog(BaseModel):
    meal_id: str
    items: List[FoodItem]
    total_macros: Macros
    total_sub_macros: Optional[SubMacros] = None
    total_calories: float = Field(..., ge=0, le=20000)
    confidence_score: float = Field(..., ge=0, le=1)
 
    @field_validator('confidence_score')
    @classmethod
    def validate_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Score must be between 0 and 1')
        return v
 
class GoalRequest(BaseModel):
    protein: float = Field(..., ge=0)
    carbs: float = Field(..., ge=0)
    fat: float = Field(..., ge=0)
    calories: float = Field(..., ge=0)

class OnboardingAttributes(BaseModel):
    age: int = Field(..., ge=0, le=120)
    height_cm: float = Field(..., ge=0)
    weight_kg: float = Field(..., ge=0)
    activity_level: float = Field(..., ge=1.0, le=2.5)
    goal: str = Field(...)

