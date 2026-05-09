"""Optional local PDF extraction (install `pdfplumber` via `pip install '.[extract]'`).

Chain-specific layouts usually need bespoke rules here; PDF sources default to skipping
unless ``--use-openai`` or you extend this module.
"""

from __future__ import annotations

from pathlib import Path

from app.macro_schema import FoodRow


def pdf_bytes_to_food_rows(_pdf: bytes, *, restaurant_name: str) -> list[FoodRow]:
    try:
        import pdfplumber  # noqa: F401, PLC0415  # pylint: disable=unused-import
    except ImportError:
        return []
    _ = (_pdf, restaurant_name)
    return []


def try_pdf_local_file(path: Path, restaurant_name: str) -> list[FoodRow]:
    if not path.is_file():
        return []
    raw = path.read_bytes()
    return pdf_bytes_to_food_rows(raw, restaurant_name=restaurant_name)
