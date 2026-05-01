from sqlmodel import Session
from app.db import engine, list_food, list_foods_single_restaurant
from app.models import Food

def protein_ratio(food: Food) -> float:
    if food.kcal_in_portion <= 0:
        return 0
    return food.protein_in_portion / food.kcal_in_portion * 100

def find_foods(
    session: Session,
    max_kcal: float,
    min_protein: float,
    restaurant_id: int | list[int] | None,
    sort_type: int,
    low_kcal_included: bool
) -> list[Food]:

    foods = list_food(session)
    kcal_protein_good_foods = [f for f in foods if not f.obsolete and f.kcal_in_portion <= max_kcal and f.protein_in_portion >= min_protein]
    print("[FOODS]", foods)
    print("[K_P_G_FOODS]", kcal_protein_good_foods)

    if low_kcal_included:
        pass
    else:
        kcal_protein_good_foods = [f for f in kcal_protein_good_foods if f.kcal_in_portion > 150]
    
    results = kcal_protein_good_foods

    if restaurant_id is None:
        pass
    elif isinstance(restaurant_id, int):
        results = [f for f in kcal_protein_good_foods if f.restaurant_id == restaurant_id]
    elif isinstance(restaurant_id, list) and all(isinstance(x, int) for x in restaurant_id):
        allowed = set(restaurant_id)
        results = [f for f in kcal_protein_good_foods if f.restaurant_id in allowed]

    return results