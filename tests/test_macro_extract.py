from pathlib import Path

import pytest

from app.extract_macros import merge_macro_rows
from app.macro_extract.html_scrapers import (
    _luca_portion_labels_grams,
    dedupe_luca_food_rows,
    discover_luca_product_urls,
    parse_hulthai_html,
    parse_luca_product_html,
    parse_max_html,
)
from app.macro_extract.image_pipeline import (
    _panprecel_rows_from_ocr_lines,
    _parse_shrimp_house_macro_line,
    nutrition_lines_to_food_rows,
)
from app.macro_schema import FoodRow

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def hulthai_html() -> str:
    return (FIXTURES / "hulthai_page.html").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def max_html() -> str:
    return (FIXTURES / "max_page.html").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def luca_product_html() -> str:
    path = FIXTURES / "luca_product_luca_traditional_en.html"
    return path.read_text(encoding="utf-8")


def test_parse_hulthai_includes_pad_thai_variants(hulthai_html: str) -> None:
    rows = parse_hulthai_html(hulthai_html)
    names = {r.food_name for r in rows}
    assert any("Pad Thai" in n and "TOFU" in n for n in names)
    assert any("Bangkok Noodles" in n and "KURCZAK" in n for n in names)


def test_parse_max_per_serving_table(max_html: str) -> None:
    rows = parse_max_html(max_html)
    assert len(rows) >= 10
    cheese = next((r for r in rows if r.food_name.strip() == "Cheeseburger"), None)
    assert cheese is not None
    assert cheese.kcal == pytest.approx(315.14)
    assert cheese.protein == pytest.approx(11.14)
    assert cheese.fats == pytest.approx(17.92)
    assert cheese.carbs == pytest.approx(26.71)


def test_parse_luca_portion_from_100g(luca_product_html: str) -> None:
    rows = parse_luca_product_html(luca_product_html)
    assert len(rows) == 1
    r = rows[0]
    assert r.food_name == "LUCA Traditional"
    assert r.kcal == pytest.approx(300.0)
    assert r.protein == pytest.approx(13.2)
    assert r.fats == pytest.approx(9.96)
    assert r.carbs == pytest.approx(39.6)


def test_discover_luca_urls_from_snippet() -> None:
    html = '<html><a href="/luca-traditional">x</a><a href="/products">y</a></html>'
    urls = discover_luca_product_urls(html, base="https://lucabakery.pl")
    assert "https://lucabakery.pl/luca-traditional" in urls


def test_luca_pipe_weight_segments() -> None:
    grams = _luca_portion_labels_grams("kawałek 140 g. | 40 cm - 950 g.")
    assert grams == [("kawałek", 140.0), ("40 cm", 950.0)]


def test_luca_slash_only_two_weights_pizza_style() -> None:
    grams = _luca_portion_labels_grams("140 g / 1100 g")
    assert grams == [("slice", 140.0), ("whole pizza", 1100.0)]


def test_shrimp_house_portion_board_line() -> None:
    line = "TEMPURA z frytkami 610 239,5 31 90 125 4,43"
    r = _parse_shrimp_house_macro_line(line, restaurant_name="Shrimp House")
    assert r is not None
    assert r.food_name == "TEMPURA z frytkami"
    assert r.size == "610 g"
    assert r.kcal == pytest.approx(1460.95)
    assert r.protein == pytest.approx(31.0)
    assert r.fats == pytest.approx(90.0)
    assert r.carbs == pytest.approx(125.0)


def test_shrimp_house_ocr_aliases_butter_carbs_te() -> None:
    """71 often OCR'd as 'Te' next to plausible P/F."""
    line = "BUTTER SHRIMP 532 141,7 37 34 Te 2,97"
    r = _parse_shrimp_house_macro_line(line, restaurant_name="Shrimp House")
    assert r is not None
    assert r.carbs == pytest.approx(71.0)
    assert r.kcal == pytest.approx(753.84)


def test_shrimp_house_ocr_aliases_pho_or_protein() -> None:
    """37 often OCR'd as the word 'or'."""
    line = "SHRIMP PHO 628 68 or 14 23 51"
    r = _parse_shrimp_house_macro_line(line, restaurant_name="Shrimp House")
    assert r is not None
    assert r.protein == pytest.approx(37.0)
    assert r.kcal == pytest.approx(round(68.0 * 628 / 100.0, 2))


def test_shrimp_house_butter_row_on_reads_as_37() -> None:
    line = "BUTTER SHRIMP 532 141,7 on 34 71 2,97"
    r = _parse_shrimp_house_macro_line(line, restaurant_name="Shrimp House")
    assert r is not None
    assert r.protein == pytest.approx(37.0)
    assert r.fats == pytest.approx(34.0)
    assert r.carbs == pytest.approx(71.0)


def test_shrimp_house_buffalo_frytkami_flat_fat_correction() -> None:
    """OCR collapses leading 7 in 77 fat (official board)."""
    line = "BUFFALO z frytkami 660 445,4 35 17 128 6,13"
    r = _parse_shrimp_house_macro_line(line, restaurant_name="Shrimp House")
    assert r is not None
    assert r.fats == pytest.approx(77.0)


def test_shrimp_house_decimal_protein_bulkie() -> None:
    line = "1/2 BUŁKI 45 255,5 3,4 0,4 23 0,6"
    r = _parse_shrimp_house_macro_line(line, restaurant_name="Shrimp House")
    assert r is not None
    assert r.protein == pytest.approx(3.4)
    assert r.kcal == pytest.approx(114.97)


def test_panprecel_dual_column_ocr_lines() -> None:
    lines = ["Z MAKIEM 318 55 FRANCUSKI 463 54", "HAWAJSKI 410 55"]
    rows = _panprecel_rows_from_ocr_lines(lines, restaurant_name="Pan Precel")
    names = sorted(r.food_name for r in rows)
    assert names == sorted(["FRANCUSKI", "HAWAJSKI", "Z MAKIEM"])
    kcal_z = next(r.kcal for r in rows if r.food_name == "Z MAKIEM")
    assert kcal_z == pytest.approx(318.0)
    assert next(r.carbs for r in rows if r.food_name == "Z MAKIEM") == pytest.approx(
        55.0
    )


def test_nutrition_lines_to_food_rows() -> None:
    lines = [
        "Sample Dish 450 30 12 40",
        "Another 200 10 5 25",
    ]
    rows = nutrition_lines_to_food_rows(lines, "TestPlace")
    assert len(rows) == 2
    assert rows[0].kcal == 450
    assert rows[0].protein == 30


def test_dedupe_luca_prefers_ascii_primary_title() -> None:
    dup = [
        FoodRow(
            restaurant_name="LUCA",
            food_name="Bajgiel z Jabłkiem",
            size="110 g",
            kcal=279.4,
            protein=6.27,
            fats=5.28,
            carbs=51.7,
        ),
        FoodRow(
            restaurant_name="LUCA",
            food_name="Bagel with apple and cinnamon filling",
            size="110 g",
            kcal=279.4,
            protein=6.27,
            fats=5.28,
            carbs=51.7,
        ),
    ]
    out = dedupe_luca_food_rows(dup)
    assert len(out) == 1
    assert out[0].food_name.startswith("Bagel with apple")


def test_merge_macro_rows_replaces_touched_only() -> None:
    existing = [
        {
            "restaurant_name": "A",
            "food_name": "keep",
            "size": "",
            "kcal": "1",
            "protein": "1",
            "fats": "1",
            "carbs": "1",
        },
        {
            "restaurant_name": "B",
            "food_name": "old",
            "size": "",
            "kcal": "2",
            "protein": "2",
            "fats": "2",
            "carbs": "2",
        },
    ]
    incoming = {
        "B": [
            FoodRow(
                restaurant_name="B",
                food_name="new",
                size=None,
                kcal=3,
                protein=3,
                fats=3,
                carbs=3,
            )
        ]
    }
    merged = merge_macro_rows(existing, incoming)
    assert any(r["food_name"] == "keep" for r in merged)
    assert not any(r["food_name"] == "old" for r in merged)
    assert any(r["food_name"] == "new" for r in merged)


def test_merge_dedupes_stale_luca_rows_even_when_not_extracted() -> None:
    shared = dict(
        size="110 g",
        kcal="279.4",
        protein="6.27",
        fats="5.28",
        carbs="51.7",
    )
    existing = [
        {**shared, "restaurant_name": "LUCA", "food_name": "Bajgiel PL"},
        {**shared, "restaurant_name": "LUCA", "food_name": "Bagel EN"},
        {
            "restaurant_name": "Z",
            "food_name": "unchanged",
            "size": "",
            "kcal": "10",
            "protein": "1",
            "fats": "1",
            "carbs": "1",
        },
    ]
    incoming = {
        "Z": [
            FoodRow(
                restaurant_name="Z",
                food_name="z-new",
                size=None,
                kcal=99,
                protein=9,
                fats=9,
                carbs=9,
            )
        ]
    }
    merged = merge_macro_rows(existing, incoming)
    luca_n = sum(1 for r in merged if r["restaurant_name"] == "LUCA")
    assert luca_n == 1
    luca_names = [r["food_name"] for r in merged if r["restaurant_name"] == "LUCA"]
    assert "Bagel EN" in luca_names or "Bagel EN" == luca_names[0]
