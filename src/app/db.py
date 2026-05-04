from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Food, Restaurant

root_path = Path(__file__).resolve().parents[2]
database_name = "main_database.db"
database_location = (root_path / "data" / database_name).resolve()
database_uri = f"sqlite:///{database_location}"

engine = create_engine(database_uri)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def add_restaurant(
    session: Session,
    name: str,
    macro_table_link: str,
    macro_table_format: str,
    notes: str,
    menu_link: str,
) -> Restaurant:
    new_restaurant = Restaurant(
        name=name,
        macro_table_link=macro_table_link,
        macro_table_format=macro_table_format,
        notes=notes,
        menu_link=menu_link,
    )
    session.add(new_restaurant)
    return new_restaurant


def list_restaurants(session: Session) -> list[Restaurant]:
    statement = select(Restaurant)
    results = list(session.exec(statement).all())
    return results


def add_food(
    session: Session,
    food_name: str,
    size: str | None,
    restaurant_id: int,
    kcal: float,
    protein: float,
    fats: float,
    carbs: float,
) -> Food:
    new_food = Food(
        food_name=food_name,
        size=size,
        restaurant_id=restaurant_id,
        kcal_in_portion=kcal,
        protein_in_portion=protein,
        fats_in_portion=fats,
        carbs_in_portion=carbs,
    )
    session.add(new_food)
    return new_food


def list_food(session: Session) -> list[Food]:
    statement = select(Food)
    results = list(session.exec(statement).all())
    return results


def list_foods_single_restaurant(session: Session, restaurant_id: int):
    results = session.exec(
        select(Food).where(Food.restaurant_id == restaurant_id)
    ).all()
    return results


def get_update_create_restaurant(
    session: Session,
    name: str,
    macro_table_link: str,
    macro_table_format: str,
    notes: str,
    menu_link: str,
):
    query_result = session.exec(
        select(Restaurant).where(Restaurant.name == name)
    ).first()
    if query_result:
        if (
            query_result.macro_table_link == macro_table_link
            and query_result.macro_table_format == macro_table_format
            and query_result.notes == notes
            and query_result.menu_link == menu_link
        ):
            return query_result
        else:
            query_result.name = name
            query_result.macro_table_link = macro_table_link
            query_result.macro_table_format = macro_table_format
            query_result.notes = notes
            query_result.menu_link = menu_link
            return query_result
    else:
        return add_restaurant(
            session, name, macro_table_link, macro_table_format, notes, menu_link
        )


def get_update_create_food(
    session: Session,
    food_name: str,
    size: str | None,
    restaurant_id: int,
    kcal: float,
    protein: float,
    fats: float,
    carbs: float,
):
    query_result = session.exec(
        select(Food).where(
            Food.food_name == food_name,
            Food.restaurant_id == restaurant_id,
            Food.size == size,
        )
    ).first()
    if query_result:
        if (
            query_result.kcal_in_portion == kcal
            and query_result.protein_in_portion == protein
            and query_result.fats_in_portion == fats
            and query_result.carbs_in_portion == carbs
        ):
            query_result.obsolete = False
            return query_result
        else:
            query_result.kcal_in_portion = kcal
            query_result.protein_in_portion = protein
            query_result.fats_in_portion = fats
            query_result.carbs_in_portion = carbs
            query_result.obsolete = False
            return query_result
    else:
        return add_food(
            session, food_name, size, restaurant_id, kcal, protein, fats, carbs
        )


if __name__ == "__main__":
    create_db_and_tables()
