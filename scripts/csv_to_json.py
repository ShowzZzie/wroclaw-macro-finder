"""Convert macros.csv to frontend/public/data/foods.json."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "macros.csv"
OUT = ROOT / "frontend" / "public" / "data" / "foods.json"


def main() -> None:
    with open(CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    data = []
    for row in rows:
        data.append(
            {
                "restaurant_name": row["restaurant_name"],
                "food_name": row["food_name"],
                "size": row["size"] if row["size"] else None,
                "kcal": float(row["kcal"]),
                "protein": float(row["protein"]),
                "fats": float(row["fats"]),
                "carbs": float(row["carbs"]),
            }
        )

    # Sort by restaurant, then food name (match export_static_json.py order)
    data.sort(key=lambda r: (r["restaurant_name"], r["food_name"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Exported {len(data)} foods → {OUT}")


if __name__ == "__main__":
    main()
