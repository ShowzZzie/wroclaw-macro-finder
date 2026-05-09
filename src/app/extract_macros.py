"""Merge-friendly macro extraction CLI (deterministic parsers by default).

Examples:

  PYTHONPATH=src python -m app.extract_macros --only \"HulThai\" \"MAX Burgers\"
  MACRO_USE_OPENAI=1 PYTHONPATH=src python -m app.extract_macros --use-openai --only KFC
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

from app.macro_extract.html_scrapers import (
    dedupe_luca_food_rows,
    fetch_and_parse_hulthai,
    fetch_and_parse_luca_catalog,
    fetch_and_parse_max,
)
from app.macro_extract.http_util import fetch_bytes
from app.macro_extract.image_pipeline import (
    OCR_OPTIONAL_SETUP,
    extract_panprecel_from_page,
    extract_shrimp_house_from_page,
)
from app.macro_extract.pdf_local import pdf_bytes_to_food_rows
from app.macro_schema import MACRO_CSV_FIELDS, FoodRow, RestaurantExtraction

root = Path(__file__).resolve().parents[2]


def _env_flag(name: str) -> bool:
    v = os.environ.get(name, "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def load_macros_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_macros_csv(path: Path, rows: Sequence[FoodRow | dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MACRO_CSV_FIELDS)
        w.writeheader()
        for r in rows:
            if isinstance(r, FoodRow):
                w.writerow(r.model_dump())
            else:
                w.writerow(r)


def _dict_to_food_row(d: dict[str, str]) -> FoodRow:
    return FoodRow(
        restaurant_name=d["restaurant_name"],
        food_name=d["food_name"],
        size=(d.get("size") or "").strip() or None,
        kcal=float(d["kcal"]),
        protein=float(d["protein"]),
        fats=float(d["fats"]),
        carbs=float(d["carbs"]),
    )


def dedupe_luca_rows_in_sheet(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Collapses leftover PL·EN twins in data/macros.csv whenever merge runs."""
    rest: list[dict[str, str]] = []
    luca: list[dict[str, str]] = []
    for r in rows:
        if r.get("restaurant_name") != "LUCA":
            rest.append(r)
        else:
            luca.append(r)
    if not luca:
        return rows
    canon = dedupe_luca_food_rows([_dict_to_food_row(d) for d in luca])
    luca_out = [
        {k: str(v) if v is not None else "" for k, v in fr.model_dump().items()}
        for fr in canon
    ]
    return rest + luca_out


def merge_macro_rows(
    existing: list[dict[str, str]],
    incoming_by_restaurant: dict[str, list[FoodRow]],
) -> list[dict[str, str]]:
    touched = set(incoming_by_restaurant.keys())
    kept = [r for r in existing if r.get("restaurant_name") not in touched]
    out = list(kept)
    for name in sorted(touched):
        for fr in incoming_by_restaurant[name]:
            row_dict = {
                k: str(v) if v is not None else "" for k, v in fr.model_dump().items()
            }
            out.append(row_dict)
    return dedupe_luca_rows_in_sheet(out)


def _pizzatopia_rows() -> list[FoodRow]:
    return [
        FoodRow(
            restaurant_name="Pizzatopia",
            food_name="High Protein Pizza",
            size=None,
            kcal=972.0,
            protein=74.0,
            fats=21.0,
            carbs=119.0,
        )
    ]


def extract_without_openai(row: dict[str, str]) -> list[FoodRow]:
    name = row["Name"]
    fmt = (row.get("Macro table format") or "").strip().lower()
    link = (row.get("Macro table link") or "").strip()

    if name == "Pizzatopia":
        return _pizzatopia_rows()
    if name == "HulThai" and link:
        return fetch_and_parse_hulthai(link)
    if name == "MAX Burgers" and link:
        return fetch_and_parse_max(link)
    if name == "LUCA":
        listing = link or "https://lucabakery.pl/products"
        return fetch_and_parse_luca_catalog(listing)
    if name == "Pan Precel":
        try:
            return extract_panprecel_from_page()
        except ImportError:
            print(f"Pan Precel: {OCR_OPTIONAL_SETUP}")
            return []
    if name == "Shrimp House":
        try:
            return extract_shrimp_house_from_page()
        except ImportError:
            print(f"Shrimp House: {OCR_OPTIONAL_SETUP}")
            return []
    if name == "McDonald's":
        mcd_pdf = root / "data" / "mcd.pdf"
        if mcd_pdf.is_file():
            raw = mcd_pdf.read_bytes()
            rows = pdf_bytes_to_food_rows(raw, restaurant_name=name)
            if rows:
                return rows
            print(
                "McDonald's: data/mcd.pdf exists but local pdfplumber extractor "
                "returns no rows; use --use-openai with the API file flow, or extend "
                "app.macro_extract.pdf_local."
            )
            return []
        print(
            "McDonald's: place the nutrition PDF at data/mcd.pdf (CDN may 403), "
            "or use --use-openai."
        )
        return []
    if fmt == "pdf" and link:
        try:
            raw = fetch_bytes(link)
        except Exception as e:
            print(f"PDF fetch failed for {name}: {e}")
            return []
        rows = pdf_bytes_to_food_rows(raw, restaurant_name=name)
        if not rows:
            print(
                f"Skipping PDF {name} (no local pdfplumber parser; "
                "use --use-openai or extend app.macro_extract.pdf_local)."
            )
        return rows
    print(f"No deterministic extractor for {name} ({fmt}).")
    return []


def run(
    *,
    use_openai: bool,
    merge: bool,
    only: set[str] | None,
    sources_path: Path,
    out_path: Path,
) -> None:
    load_dotenv()
    from app import api_pdfs  # noqa: PLC0415

    incoming: dict[str, list[FoodRow]] = {}
    sources_rows: list[dict[str, str]] = []
    with open(sources_path, newline="", encoding="utf-8") as f:
        sources_rows = list(csv.DictReader(f))

    for row in sources_rows:
        name = row["Name"]
        if only is not None and name not in only:
            continue
        print(f"Extracting: {name}")
        foods: list[FoodRow] = []
        try:
            if use_openai and (
                (row.get("Macro table format") or "").lower() == "pdf"
                or row["Name"]
                in {
                    "McDonald's",
                    "KFC",
                    "Pasibus",
                    "Popeye's",
                    "Pizza Hut",
                }
            ):
                client = api_pdfs.get_openai_client()
                parsed: RestaurantExtraction = api_pdfs.extract_restaurant_openai(
                    row, client
                )
                foods = list(parsed.foods)
            else:
                foods = extract_without_openai(row)
        except Exception as e:
            print(f"  fail: {e}")
            foods = []
        if foods:
            incoming[name] = foods
            print(f"  -> ok: {len(foods)} foods for {name}")
        else:
            print(f"  -> no rows for {name}")

    total_new = sum(len(v) for v in incoming.values())
    if merge:
        existing = load_macros_csv(out_path)
        # Touched chains: drop their old CSV block, append only rows from this run.
        for chain in sorted(incoming.keys()):
            prev_n = sum(
                1 for r in existing if (r.get("restaurant_name") or "") == chain
            )
            new_n = len(incoming[chain])
            net = new_n - prev_n
            print(
                f"  merge replace: `{chain}` had {prev_n} row(s) in CSV "
                f"→ writing {new_n} (net {net:+d})"
            )
        combined = merge_macro_rows(existing, incoming)
        write_macros_csv(out_path, combined)
        n_rest = len(incoming)
        print(f"Updated {out_path} ({n_rest} chain(s) replaced, {total_new} foods).")
    else:
        flat: list[FoodRow] = []
        for lst in incoming.values():
            flat.extend(lst)
        write_macros_csv(out_path, flat)
        nr = len(incoming)
        print(f"Wrote {out_path} only ({total_new} foods, {nr} restaurant(s)).")


def main(argv: Sequence[str] | None = None) -> None:
    desc = "Extract restaurant macros into data/macros.csv"
    p = argparse.ArgumentParser(description=desc)
    p.add_argument(
        "--use-openai",
        action="store_true",
        help="Call OpenAI for supported PDF chains (requires OPENAI_SECRET_KEY).",
    )
    p.add_argument(
        "--no-merge",
        action="store_true",
        help="Write only rows from this run (default: merge with existing macros.csv).",
    )
    p.add_argument(
        "--only",
        nargs="+",
        metavar="NAME",
        help="Restaurant name(s) exactly as in data/sources.csv",
    )
    p.add_argument(
        "--sources",
        type=Path,
        default=root / "data" / "sources.csv",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=root / "data" / "macros.csv",
    )
    args = p.parse_args(list(argv) if argv is not None else None)
    use_openai = args.use_openai or _env_flag("MACRO_USE_OPENAI")
    run(
        use_openai=use_openai,
        merge=not args.no_merge,
        only=set(args.only) if args.only else None,
        sources_path=args.sources.resolve(),
        out_path=args.out.resolve(),
    )


if __name__ == "__main__":
    main()
