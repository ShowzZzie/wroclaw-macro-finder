from typing import Optional

from pydantic import BaseModel


class FoodRow(BaseModel):
    restaurant_name: str
    food_name: str
    size: Optional[str] = None
    kcal: float
    protein: float
    fats: float
    carbs: float


class RestaurantExtraction(BaseModel):
    restaurant_name: str
    foods: list[FoodRow]


MACRO_CSV_FIELDS = [
    "restaurant_name",
    "food_name",
    "size",
    "kcal",
    "protein",
    "fats",
    "carbs",
]
