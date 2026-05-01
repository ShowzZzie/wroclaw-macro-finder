"""
find_foods(
    session,
    max_kcal,
    min_protein,
    optional restaurant filter,
    sort mode
)

---

It should:

ignore obsolete=True
filter by kcal/protein
sort by something simple first, like highest protein or best protein-per-kcal
return matching Food rows  

"""

from sqlmodel import Session
from app.db import engine, list_food, list_foods_single_restaurant
from app.models import Food

def find_foods(
    session: Session,
    max_kcal: float,
    min_protein: float,
    restaurant_id: int | list[int],
    sort_type: str |  None
) -> list[Food]:

    foods = list_food(session)
    kcal_protein_good_foods = [f for f in foods if not f.obsolete and f.kcal_in_portion <= max_kcal and f.protein_in_portion >= min_protein]
    print("[FOODS]", foods)
    print("[K_P_G_FOODS]", kcal_protein_good_foods)
    
    if isinstance(restaurant_id, int):
        restau_good_foods = [f for f in kcal_protein_good_foods if f.restaurant_id == restaurant_id]
        print(restau_good_foods)
    elif isinstance(restaurant_id, list) and all(isinstance(x, int) for x in restaurant_id):
        restau_good_foods = []
        for id in restaurant_id:
            restau_good_foods.append(f for f in kcal_protein_good_foods if f.restaurant_id == id)
        print(restau_good_foods)

    
    return 0