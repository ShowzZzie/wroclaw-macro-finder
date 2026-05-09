"""Update Subway sub/submelt items: set size='15cm' and add 30cm duplicates."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "macros.csv"


def is_sub_item(food_name: str) -> bool:
    """Return True if the food name indicates a Sub or SubMelt product."""
    lower = food_name.lower()
    return "sub" in lower or "submelt" in lower


def main() -> None:
    with open(CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    assert fieldnames is not None

    new_rows: list[dict[str, str]] = []
    updated = 0

    for row in rows:
        if row["restaurant_name"] == "Subway" and is_sub_item(row["food_name"]):
            # Set existing row to 15cm
            row["size"] = "15cm"
            new_rows.append(row)

            # Create 30cm duplicate with doubled macros
            doubled = dict(row)
            doubled["size"] = "30cm"
            for col in ("kcal", "protein", "fats", "carbs"):
                doubled[col] = str(float(row[col]) * 2)
            new_rows.append(doubled)
            updated += 1
        else:
            new_rows.append(row)

    # Sort by restaurant, then food name
    new_rows.sort(
        key=lambda r: (r["restaurant_name"], r["food_name"], r.get("size", ""))
    )

    with open(CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_rows)

    print(f"Updated {updated} Subway subs → 15cm + 30cm duplicates")
    print(f"Total rows: {len(new_rows)}")


if __name__ == "__main__":
    main()
