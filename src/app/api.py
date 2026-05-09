from typing import Annotated, Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.db import engine, list_restaurants
from app.schemas import FoodSearchResult, RestaurantOption
from app.search import find_foods, protein_ratio

app = FastAPI(title="Wrocław Macro Finder API")

# Dev-only CORS: Vite dev server runs on :5173. In production the SPA is
# served as static files from the same origin, so this is a no-op there.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/restaurants", response_model=list[RestaurantOption])
def get_restaurants():
    with Session(engine) as session:
        return [
            RestaurantOption(
                id=r.id,
                name=r.name,
                menu_link=r.menu_link or None,
                macro_table_link=r.macro_table_link or None,
            )
            for r in list_restaurants(session)
            if r.id is not None
        ]


@app.get("/foods/search", response_model=list[FoodSearchResult])
def get_foods(
    max_kcal: Annotated[float, Query(gt=0, le=3000)],
    min_protein: Annotated[float, Query(gt=0, le=300)],
    restaurant_id: Annotated[int | None, Query(gt=0)] = None,
    low_kcal_included: bool = False,
    limit: Annotated[int, Query(ge=1, le=250)] = 10,
    sort_by: Literal[
        "protein_ratio_desc", "protein_desc", "kcal_asc", "kcal_desc"
    ] = "protein_ratio_desc",
):
    with Session(engine) as session:
        results_food = find_foods(
            session=session,
            max_kcal=max_kcal,
            min_protein=min_protein,
            restaurant_id=restaurant_id,
            low_kcal_included=low_kcal_included,
            limit=limit,
            sort_by=sort_by,
        )

        restaurant_names = {r.id: r.name for r in list_restaurants(session)}

        results_fsr = [
            FoodSearchResult(
                restaurant_name=restaurant_names[item.restaurant_id],
                food_name=item.food_name,
                size=item.size,
                kcal=item.kcal_in_portion,
                protein=item.protein_in_portion,
                fats=item.fats_in_portion,
                carbs=item.carbs_in_portion,
                protein_per_100_kcal=round(protein_ratio(item), 2),
            )
            for item in results_food
        ]

    return results_fsr
