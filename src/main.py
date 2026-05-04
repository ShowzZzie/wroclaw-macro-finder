import argparse

from sqlmodel import Session

from app.db import create_db_and_tables, engine, list_restaurants
from app.ingest import import_foods, import_restaurants
from app.search import find_foods


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
            restaurant_id=int(s)
            if (s := input("Any specific restaurant? (enter to skip): ").strip())
            else None,  # 📝 TO-DO: implement list of ints logic
            low_kcal_included=bool(
                int(
                    input(
                        "Include items ≤150 kcal (sauces/small add-ons)? 1=yes, 0=no: "
                    ).strip()
                    or "0"
                )
            ),
            limit=int(s)
            if (s := input("Show N results (default: 10), n= ").strip())
            else None,
            sort_by=input(
                "Sorting type "
                "(protein_ratio_desc, protein_desc, kcal_asc, kcal_desc), "
                "default = protein_ratio_desc: "
            ),
        )
        restaurant_names = {r.id: r.name for r in list_restaurants(session_find_food)}

    print("restaurant_name | food_name | size | kcal | protein | protein_per_100_kcal")
    for i in good_foods:
        print(
            f"{restaurant_names[i.restaurant_id]} | {i.food_name} | {i.size} | "
            f"{i.kcal_in_portion} | {i.protein_in_portion} | "
            f"{round(i.protein_in_portion / i.kcal_in_portion * 100, 2)}"
        )
    print("Items found:", len(good_foods))
    print("Goodbye from Wrocław Macro Finder!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reingest-database",
        action="store_true",
        help="Use if you want to re-import CSVs into database",
    )
    args = parser.parse_args()
    main(args)
