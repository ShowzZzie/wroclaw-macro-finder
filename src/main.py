from app.db import create_db_and_tables, engine, list_restaurants
from app.ingest import import_restaurants, import_foods
from sqlmodel import Session
from app.search import find_foods
import argparse

def main(args):
    print("Hello from Wrocław Macro Finder!")
    
    create_db_and_tables()
    
    if args.reingest_database:
        print("[LOGGER] Reingesting database")
        with Session(engine) as session_import:
            import_restaurants(session_import)
            session_import.flush()
            import_foods(session_import)
            session_import.commit()

    with Session(engine) as session_find_food:
        good_foods = find_foods(
            session=session_find_food,
            max_kcal=float(input("Maximum KCAL: ")),
            min_protein=float(input("Minimum PROTEIN: ")),
            restaurant_id = int(s) if (s := input("Any specific restaurant? (enter to skip): ").strip()) else None, # 📝 TO-DO: implement list of ints logic
            low_kcal_included = bool(int(input("Include items ≤150 kcal (sauces/small add-ons)? 1=yes, 0=no: ").strip() or "0")),
            limit = int(input("Show N results (default: 10), n= ")),
            sort_by = input("Sorting type (protein_ratio_desc, protein_desc, kcal_asc, kcal_desc): ")
        )
        restaurant_names = {r.id: r.name for r in list_restaurants(session_find_food)}

    print("restaurant_name | food_name | size | kcal | protein | protein_per_100_kcal")
    for item in good_foods:
        print(f"{restaurant_names[item.restaurant_id]} | {item.food_name} | {item.size} | {item.kcal_in_portion} | {item.protein_in_portion} | {round(item.protein_in_portion/item.kcal_in_portion*100, 2)}") 
    print("Items found:", len(good_foods))
    print("Goodbye from Wrocław Macro Finder!")



if __name__ == "__main__": 
    parser = argparse.ArgumentParser()
    parser.add_argument("--reingest-database", action="store_true", help="Use if you want to re-import CSVs into database")
    args = parser.parse_args()
    main(args)
