import csv
from pathlib import Path
from app.db import get_update_create_food, get_update_create_restaurant
from sqlmodel import Session

root = Path(__file__).resolve().parents[2]
sources = Path(root / "data" / "sources.csv").resolve()
foods = Path(root / "data" / "macros.csv").resolve()

def read_restaurants_into_list() -> list[dict]:
    restaurants = []
    with open(sources) as src:
        src_reader = csv.DictReader(src)
        for dic in src_reader:
            restaurants.append(
                {
                    "name": dic["Name"],
                    "macro_link": dic["Macro table link"],
                    "macro_format": dic["Macro table format"],
                    "notes": dic["Notes"],
                    "menu": dic["Menu"]
                }   
            )
    return restaurants


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


def import_foods(session: Session) -> None:
    # 6. import_foods() needs a restaurant-name → id mapping
    return None



"""
CORRECT FLOW:

create tables
open session
read sources.csv
upsert restaurants
flush/commit
build restaurant_name -> restaurant_id mapping
read macros.csv
upsert food rows using resolved restaurant_id
commit
"""