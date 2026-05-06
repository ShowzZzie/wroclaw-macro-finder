import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Food, Restaurant
from app.search import find_foods, protein_ratio


@pytest.fixture
def test_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        restaurant = Restaurant(
            name="Test KFC",
            macro_table_link="x",
            macro_table_format="pdf",
            notes="x",
            menu_link="x",
        )
        session.add(restaurant)
        session.flush()
        assert restaurant.id is not None

        restaurant_2 = Restaurant(
            name="Test MCD",
            macro_table_link="y",
            macro_table_format="jpg",
            notes="y",
            menu_link="y",
        )
        session.add(restaurant_2)
        session.flush()
        assert restaurant_2.id is not None

        session.add_all(
            [
                Food(
                    food_name="High Protein Chicken",
                    size=None,
                    restaurant_id=restaurant.id,
                    kcal_in_portion=500,
                    protein_in_portion=50,
                    fats_in_portion=10,
                    carbs_in_portion=40,
                ),
                Food(
                    food_name="Sub Fries",
                    size=None,
                    restaurant_id=restaurant.id,
                    kcal_in_portion=125,
                    protein_in_portion=11,
                    fats_in_portion=15,
                    carbs_in_portion=100,
                ),
                Food(
                    food_name="Average Meat",
                    size="150g",
                    restaurant_id=restaurant.id,
                    kcal_in_portion=300,
                    protein_in_portion=60,
                    fats_in_portion=20,
                    carbs_in_portion=5,
                ),
                Food(
                    food_name="Monster",
                    size="Large",
                    restaurant_id=restaurant_2.id,
                    kcal_in_portion=1500,
                    protein_in_portion=148,
                    fats_in_portion=46.7,
                    carbs_in_portion=168.7,
                ),
                Food(
                    food_name="Obsolete Burger",
                    size=None,
                    restaurant_id=restaurant_2.id,
                    kcal_in_portion=420,
                    protein_in_portion=69,
                    fats_in_portion=6,
                    carbs_in_portion=9,
                    obsolete=True,
                ),
            ]
        )

        session.commit()

        yield session


def test_protein_ratio():
    test_food = Food(
        food_name="TPR FOOD",
        size=None,
        restaurant_id=0,
        kcal_in_portion=650,
        protein_in_portion=78,
        fats_in_portion=28,
        carbs_in_portion=86,
    )
    assert protein_ratio(test_food) == pytest.approx(12.0)


def test_protein_ratio_0kcal():
    test_food = Food(
        food_name="TPR 0 FOOD",
        size=None,
        restaurant_id=0,
        kcal_in_portion=0,
        protein_in_portion=100,
        fats_in_portion=10,
        carbs_in_portion=50,
    )
    assert protein_ratio(test_food) == pytest.approx(0)


def test_find_foods_800kcal_incl(test_session: Session):
    results = find_foods(
        session=test_session,
        max_kcal=800,
        min_protein=10,
        restaurant_id=None,
        low_kcal_included=True,
        limit=10,
        sort_by="protein_ratio_desc",
    )
    assert len(results) == 3
    assert {f.food_name for f in results} == {
        "High Protein Chicken",
        "Average Meat",
        "Sub Fries",
    }


def test_find_foods_800kcal_excl(test_session: Session):
    results = find_foods(
        session=test_session,
        max_kcal=800,
        min_protein=10,
        restaurant_id=None,
        low_kcal_included=False,
        limit=10,
        sort_by="protein_ratio_desc",
    )
    assert len(results) == 2
    assert {f.food_name for f in results} == {"High Protein Chicken", "Average Meat"}


def test_find_foods_restaurant_filter(test_session: Session):
    statement = select(Restaurant).where(Restaurant.name == "Test MCD")
    row = test_session.exec(statement).first()
    assert row is not None
    expected_id = row.id
    assert expected_id is not None

    results = find_foods(
        session=test_session,
        max_kcal=1700,
        min_protein=10,
        restaurant_id=expected_id,
        low_kcal_included=True,
        limit=10,
        sort_by="protein_ratio_desc",
    )
    assert len(results) == 1
    assert all(f.restaurant_id == expected_id for f in results)
    assert results[0].food_name == "Monster"


def test_find_foods_ratio_sorting(test_session: Session):
    results = find_foods(
        session=test_session,
        max_kcal=1700,
        min_protein=10,
        restaurant_id=None,
        low_kcal_included=True,
        limit=10,
        sort_by="protein_ratio_desc",
    )

    ratios = [protein_ratio(f) for f in results]

    assert len(results) == 4
    assert ratios == sorted(ratios, reverse=True)


def test_find_foods_protein_desc_sorting(test_session: Session):
    results = find_foods(
        session=test_session,
        max_kcal=1700,
        min_protein=10,
        restaurant_id=None,
        low_kcal_included=True,
        limit=10,
        sort_by="protein_desc",
    )

    proteins = [f.protein_in_portion for f in results]

    assert len(results) == 4
    assert proteins == sorted(proteins, reverse=True)


def test_find_foods_kcal_desc_sorting(test_session: Session):
    results = find_foods(
        session=test_session,
        max_kcal=1700,
        min_protein=10,
        restaurant_id=None,
        low_kcal_included=True,
        limit=10,
        sort_by="kcal_desc",
    )

    kcals = [f.kcal_in_portion for f in results]

    assert len(results) == 4
    assert kcals == sorted(kcals, reverse=True)


def test_find_foods_kcal_asc_sorting(test_session: Session):
    results = find_foods(
        session=test_session,
        max_kcal=1700,
        min_protein=10,
        restaurant_id=None,
        low_kcal_included=True,
        limit=10,
        sort_by="kcal_asc",
    )

    kcals = [f.kcal_in_portion for f in results]

    assert len(results) == 4
    assert kcals == sorted(kcals, reverse=False)


def test_find_foods_limit(test_session: Session):
    results = find_foods(
        session=test_session,
        max_kcal=1700,
        min_protein=10,
        restaurant_id=None,
        low_kcal_included=True,
        limit=2,
        sort_by="kcal_asc",
    )

    assert len(results) == 2


def test_find_foods_skips_obsolete(test_session: Session):
    obsolete = test_session.exec(
        select(Food).where(Food.food_name == "Obsolete Burger")
    ).first()

    assert obsolete is not None
    assert obsolete.obsolete is True

    assert obsolete.kcal_in_portion <= 1700
    assert obsolete.protein_in_portion >= 10

    results = find_foods(
        session=test_session,
        max_kcal=1700,
        min_protein=10,
        restaurant_id=None,
        low_kcal_included=True,
        limit=10,
        sort_by="protein_ratio_desc",
    )
    assert "Obsolete Burger" not in {f.food_name for f in results}
