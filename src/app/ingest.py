import csv
from pathlib import Path
from app.db import get_update_create_food, get_update_create_restaurant, list_restaurants
from sqlmodel import Session

root = Path(__file__).resolve().parents[2]
sources = Path(root / "data" / "sources.csv").resolve()
foods = Path(root / "data" / "macros.csv").resolve()


def import_restaurants(session: Session) -> None:
    with open(sources) as src:
        src_reader = csv.DictReader(src)
        for dic in src_reader:
            get_update_create_restaurant(
                session=session,
                name=dic["Name"],
                macro_table_link=dic["Macro table link"],
                macro_table_format=dic["Macro table format"],
                notes=dic["Notes"],
                menu_link=dic["Menu"]
            )


def import_foods(session: Session):
    restaurants = list_restaurants(session)
    restaurant_ids = {
        restaurant.name: restaurant.id for restaurant in restaurants
    }

    with open(foods) as f:
        food_reader = csv.DictReader(f)
        for dic in food_reader:
            res_id = restaurant_ids[dic["restaurant_name"]]
            get_update_create_food(
                session=session,
                food_name=dic["food_name"],
                size=dic["size"] or None,
                restaurant_id=res_id,
                kcal=float(dic["kcal"]),
                protein=float(dic["protein"]),
                fats=float(dic["fats"]),
                carbs=float(dic["carbs"])
            )