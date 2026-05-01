import csv
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sources = Path(root / "data" / "sources.csv").resolve()

restaurants = []

with open(sources) as src:
    src_reader = csv.DictReader(src)
    for dic in src_reader:
        restaurants.append(
            {
                "name": dic["Name"],
                "macro_link": dic["Macro table link"],
                "macro_format": dic["Macro table format"],
                "notes": dic["Notes"],
                "menu": dic["Menu"]
            }
        )


def import_restaurants() -> None:
    return None


def import_foods() -> None:
    return None