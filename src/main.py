from app.db import create_db_and_tables
from app.ingest import import_restaurants, import_foods

def main():
    print("Hello from Wrocław Macro Finder!")
    create_db_and_tables()
    import_restaurants()
    import_foods()



if __name__ == "__main__":
    main()
