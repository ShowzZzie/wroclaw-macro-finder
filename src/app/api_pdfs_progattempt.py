# take sources.csv
# take links and notes from each restaurant
# send them to OpenAI API, parse the response and create macros.csv
# only then import sources.csv and marcos.csv into a DB
# keep sources.csv as the source of truth, create macros.csv from that file, then import both into DB
from openai import OpenAI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from pathlib import Path
import csv
from typing import Optional

class FoodRow(BaseModel):
    restaurant_name: str
    food_name: str
    size: Optional[str] = None
    kcal: float
    protein: float
    fats: float
    carbs: float

class RestaurantExtraction(BaseModel):
    restaurant_name: str
    foods: list[FoodRow]

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_SECRET_KEY"])

root = Path(__file__).resolve().parents[2]
sources = Path(root / "data" / "sources.csv").resolve()

def build_prompt(name: str, notes: str) -> str:
    return f"""
You are extracting nutrition data from one restaurant macro table.

Restaurant name:
{name}

Operator notes:
{notes}

Return ONLY structured data matching the schema.

Rules:
1. Extract one row per actual food/menu item.
2. restaurant_name must be exactly: "{name}"
3. size should be null if the source does not provide a meaningful size/variant.
4. kcal, protein, fats, carbs must be numeric.
5. Ignore columns not needed for the schema.
6. Do not invent values.
7. If an item lacks the required kcal/protein/fats/carbs fields, omit that item.
8. Do not include commentary or explanations.

Exceptions:
1. For Pizza Hut, the linked calories table will contain only data per 100g. The data on weight of each item is listed in a separate table, which can be found at "https://pizzahut.pl/alergeny-wartosci-odzywcze" in the hyperlink of "Gramatury - pobierz plik". You must combine per item data from both files and only then give proper output, with item name and per portion kcal, protein, fats and carbs.
2. For LUCA, you must enter each item listed in the menu by clicking "Zobacz więcej". On the item page, you must click "Więcej Informacji", there you'll see weight of the item, and per 100g macros. Additionally, you may notice items that are combinations of two different items, usually noticeable by a "+" sign - the macro for them is just addition of the macros of items they combine.
3. For Pizzatopia, they have only one item to add: "High Protein Pizza", containing 972 kcal, 74g protein, 21g fats, 119g carbs. Add only that one item.
4. For Pasibus, the pdf has two pages. Please extract both pages, previous extractions contained only the second page.
5. For plain text format, the data is on the page you open.
6. For PNG format, you must look at the images that are on the linked site, and extract data from them.

""".strip()


def extract_restaurant(row: dict) -> RestaurantExtraction: # determine what handler the row should be routed to
    # TRY SWITCH INSTEAD OF THIS
    if row["Macro table format"] == "pdf":
        return extract_restaurant_pdf(row)
    elif row["Macro table format"] == "plain text on this subpage":
        return extract_restaurant_plaintext(row)
    elif row["Macro table format"] in ["images", "png"]:
        return extract_restaurant_img(row)
    elif row["Macro table format"] == "n/a" and row["Name"] == "LUCA":
        return extract_restaurant_LUCA(row)
    elif row["Name"] == "Pizzatopia":
        return extract_restaurant_PIZZATOPIA()
    else:
        raise ValueError("[EXTRACT_RESTAURANT] Unexpected format encountered")

def extract_restaurant_pdf(row: dict) -> RestaurantExtraction: # send input_file or fetched bytes for PDF.
    prompt = build_prompt(
        name=row["Name"],
        notes=row.get("Notes", "") or ""
    )

    response = client.responses.parse(
        model="gpt-5.4-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_file",
                        "file_url": row["Macro table link"]
                    },
                ],
            }
        ],
        text_format=RestaurantExtraction
    )
    print("[RESPONSE PRINTER]", response)

    return response.output_parsed

def extract_restaurant_plaintext(row: dict) -> RestaurantExtraction: # fetch HTML/text first, then send as input_text (optionally trimmed/cleaned).
    return 1

def extract_restaurant_img(row: dict) -> RestaurantExtraction: # send input_image for png/images links.
    return 1 # replace links to pages with links to images themselves

def extract_restaurant_LUCA(row: dict) -> RestaurantExtraction:
    return 1

def extract_restaurant_PIZZATOPIA():
    return RestaurantExtraction(
        restaurant_name="Pizzatopia", 
        foods=[
            FoodRow(
                restaurant_name="Pizzatopia",
                food_name="High Protein Pizza",
                size=None,
                kcal=972.0,
                protein=74.0,
                fats=21.0,
                carbs=119.0)])


def main() -> None:
    with open(sources, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_foods: list[FoodRow] = []

        for row in reader:
            print(f"Extracting: {row['Name']}")
            try:
                parsed = extract_restaurant(row)
                all_foods.extend(parsed.foods)
            except ValueError as e:
                print(e)

        out_path = root / "data" / "macros.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as out_file:
            writer = csv.DictWriter(
                out_file,
                fieldnames=[
                    "restaurant_name",
                    "food_name",
                    "size",
                    "kcal",
                    "protein",
                    "fats",
                    "carbs",
                ],
            )
            writer.writeheader()
            for food in all_foods:
                writer.writerow(food.model_dump())


if __name__ == "__main__":
    main()