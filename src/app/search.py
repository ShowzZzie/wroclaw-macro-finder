from sqlmodel import Session
from app.db import list_food
from app.models import Food

def protein_ratio(food: Food) -> float:
    if food.kcal_in_portion <= 0:
        return 0
    return food.protein_in_portion / food.kcal_in_portion * 100

def calc_and_sort_by_protein_ratio(foods: list[Food]) -> list[Food]:
    # function meant to take in result (i.e. list of Foods), and order them by protein ratio
    foods_sorted = sorted(foods, key=protein_ratio, reverse=True)
    return foods_sorted

def find_foods(
    session: Session,
    max_kcal: float,
    min_protein: float,
    restaurant_id: int | list[int] | None,
    low_kcal_included: bool,
    limit: int,
    sort_by: str
) -> list[Food]:

    foods = list_food(session)
    kcal_protein_good_foods = [f for f in foods if not f.obsolete and f.kcal_in_portion <= max_kcal and f.protein_in_portion >= min_protein]

    if not low_kcal_included:
        kcal_protein_good_foods = [f for f in kcal_protein_good_foods if f.kcal_in_portion > 150]
    
    results = kcal_protein_good_foods

    if restaurant_id is None:
        pass
    elif isinstance(restaurant_id, int):
        results = [f for f in kcal_protein_good_foods if f.restaurant_id == restaurant_id]
    elif isinstance(restaurant_id, list) and all(isinstance(x, int) for x in restaurant_id):
        allowed = set(restaurant_id)
        results = [f for f in kcal_protein_good_foods if f.restaurant_id in allowed]

    sorted_results = calc_and_sort_by_protein_ratio(results)

    return sorted_results[:limit]