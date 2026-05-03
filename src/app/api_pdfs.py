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

""".strip()


def extract_restaurant(row: dict) -> RestaurantExtraction:
    prompt = build_prompt(name=row["Name"], notes=row.get("Notes", "") or "")

    if row["Name"] == "McDonald's":
        mcd_file = Path(root / "data" / "mcd.pdf").resolve()
        with open(mcd_file, "rb") as f:
            mcd_file_uploaded = client.files.create(
                file=f,
                purpose="user_data",
            )
        response = client.responses.parse(
            model="gpt-5.4-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_file", "file_id": mcd_file_uploaded.id},
                    ],
                },
            ],
            text_format=RestaurantExtraction,
        )
    elif row["Name"] == "KFC":
        kfc_prompt = (
            prompt
            + """\n\n
            KFC (Poland PDF)
            - Read all pages/sections. Do not merge rows; same item text under different gray banner = separate rows.
            - kcal: only Energy [kcal] → porcja. Never Energy [kJ] → porcja for kcal.
            - protein / fats / carbs: Białko / Tłuszcz / Węglowodany → porcja each (total fat & total carbs; not saturated/sugars sub-rows unless that row is all you have).
            - Gray banner Kentucky / Kawałki … → food_name "<item> (Kentucky)". Banner Hot&Spicy / H&S → "<item> (Hot&Spicy)". Else item text only, no suffix.
            - size: Średnia waga porcji (g) → "NNN g" when present.
            """
        )

        response = client.responses.parse(
            model="gpt-5.4",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": kfc_prompt},
                        {"type": "input_file", "file_url": row["Macro table link"]},
                    ],
                },
            ],
            text_format=RestaurantExtraction,
        )
    elif row["Name"] == "Pasibus":
        pasi_prompt = (
            prompt
            + """\n\n
        Pasibus exception:
        - The provided PDF contains exactly 2 pages.
        - Extract nutrition rows from BOTH page 1 and page 2.
        - Do not return output after reading only one page.
        - Before finalizing, verify that rows were collected from both pages.
        - If an item appears on both pages, keep distinct variants/sizes as separate rows."""
        )

        response = client.responses.parse(
            model="gpt-5.4-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": pasi_prompt},
                        {"type": "input_file", "file_url": row["Macro table link"]},
                    ],
                },
            ],
            text_format=RestaurantExtraction,
        )
    elif row["Name"] == "Popeye's":
        popeye_prompt = (
            prompt
            + """\n\n
        Popeye’s exception:
            - Extract from all categories/tables across the full document, not only the first section.
            - Do not stop after wings/tenders/nuggets; continue through the entire PDF
            Energy (kcal vs kJ):
                - Field kcal must be kilocalories per portion, not kilojoules.
                - If the table shows energy per portion only in kJ, convert: kcal = kJ / 4.184.
                - If both kJ and kcal appear for the portion, use the kcal value only."""
        )

        response = client.responses.parse(
            model="gpt-5.4-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": popeye_prompt},
                        {"type": "input_file", "file_url": row["Macro table link"]},
                    ],
                },
            ],
            text_format=RestaurantExtraction,
        )
    elif row["Name"] == "Pizza Hut":
        weight_pdf_link = "https://amrestcdn.azureedge.net/ph-web-ordering/Pizza_Hut_PL/2026/T_mobile/GRAMATURY.pdf"
        p_h_prompt = (
            prompt + "\n\nPizza Hut special instructions:\n"
            f"- Nutrition PDF (per 100g): {row['Macro table link']}\n"
            f"- Weights PDF (portion grams): {weight_pdf_link}\n"
            "- Match items between the two PDFs by name/variant.\n"
            "- Compute per-portion values using: value_per_portion = value_per_100g * portion_grams / 100.\n"
            "- Return only per-portion kcal/protein/fats/carbs.\n"
            "- If an item cannot be confidently matched across PDFs, omit it.\n"
            "- Round numeric outputs to 1 decimal place.\n"
        )
        response = client.responses.parse(
            model="gpt-5.4-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": p_h_prompt},
                        {"type": "input_file", "file_url": weight_pdf_link},
                        {"type": "input_file", "file_url": row["Macro table link"]},
                    ],
                }
            ],
            text_format=RestaurantExtraction,
        )
    elif row["Macro table format"].lower() == "pdf":
        response = client.responses.parse(
            model="gpt-5.4-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_file", "file_url": row["Macro table link"]},
                    ],
                }
            ],
            text_format=RestaurantExtraction,
        )
        print("[RESPONSE PRINTER]", response)
    elif row["Name"] == "Pizzatopia":
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
                    carbs=119.0,
                )
            ],
        )
    else:
        raise ValueError(
            f"Skipping non-PDF format: {row['Macro table format']} for {row['Name']}"
        )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("Empty response.output_parsed")
    return parsed


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
            except Exception as e:
                print(f"Weird fail for {row['Name']}:", e)

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
