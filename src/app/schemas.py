from pydantic import BaseModel


class FoodSearchResult(BaseModel):
    restaurant_name: str
    food_name: str
    size: str | None = None
    kcal: float
    protein: float
    fats: float
    carbs: float
    protein_per_100_kcal: float
