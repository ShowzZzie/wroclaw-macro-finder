from sqlmodel import SQLModel, Field

class Restaurant(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    macro_table_link: str
    macro_table_format: str
    notes: str
    menu_link: str


class Food(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    food_name: str
    size: str | None = Field(default=None)
    restaurant_id: int = Field(foreign_key="restaurant.id", index=True)
    kcal_in_portion: float
    protein_in_portion: float
    fats_in_portion: float
    carbs_in_portion: float
    obsolete: bool = Field(default=False) # for the future, if the given position was removed by the restaurant