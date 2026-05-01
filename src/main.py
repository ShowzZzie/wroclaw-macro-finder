from app.db import create_db_and_tables, engine
from app.ingest import import_restaurants, import_foods
from sqlmodel import Session

def main():
    print("Hello from Wrocław Macro Finder!")
    
    create_db_and_tables()
    
    with Session(engine) as session:
        import_restaurants(session)
        import_foods(session)
        session.commit()



if __name__ == "__main__":
    main()
