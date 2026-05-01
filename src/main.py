from app.db import create_db_and_tables, engine
from app.ingest import import_restaurants, import_foods
from sqlmodel import Session
from app.search import find_foods

def main():
    print("Hello from Wrocław Macro Finder!")
    
    create_db_and_tables()
    
    with Session(engine) as session_import:
        import_restaurants(session_import)
        session_import.flush()
        import_foods(session_import)
        session_import.commit()

    with Session(engine) as session_find_food:
        find_foods(
            session=session_find_food,
            max_kcal=float(input("Maximum KCAL: ")),
            min_protein=float(input("Minimum PROTEIN: ")),
            restaurant_id = int(s) if (s := input("Any specific restaurant? (enter to skip): ").strip()) else None,
            sort_type=0
        )

    print("Goodbye from Wrocław Macro Finder!")



if __name__ == "__main__": 
    main()
