"""Export the SQLite database to a static JSON file for the frontend."""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "main_database.db"
OUT = ROOT / "frontend" / "public" / "data" / "foods.json"


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT
            f.food_name,
            f.size,
            f.kcal_in_portion  AS kcal,
            f.protein_in_portion AS protein,
            f.fats_in_portion  AS fats,
            f.carbs_in_portion AS carbs,
            r.name             AS restaurant_name
        FROM food f
        JOIN restaurant r ON f.restaurant_id = r.id
        WHERE f.obsolete = 0
        ORDER BY r.name, f.food_name
        """
    ).fetchall()
    conn.close()

    data = [dict(r) for r in rows]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Exported {len(data)} foods → {OUT}")


if __name__ == "__main__":
    main()
