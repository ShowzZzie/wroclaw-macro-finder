import base64
import io
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from app.macro_extract.http_util import fetch_bytes
from app.macro_schema import FoodRow, RestaurantExtraction


def _fix_pasibus_sauces(rows: list[FoodRow]) -> list[FoodRow]:
    """Idempotent cleanup for Pasibus sauce rows.

    The vision model sometimes misreads the PDF columns for sauce items,
    producing rows where protein and fats are swapped, or emitting both
    a per-100g row (no size) and a per-portion row (size = "35 g") for the
    same sauce.

    Rules applied:
    1. If a sauce exists both WITH and WITHOUT a size, drop the unsized row
       (it's typically a per-100g mis-extraction with wrong column mapping).
    2. For any remaining unsized sauce where protein > fats, swap them —
       mayo-based sauces always have more fat than protein.
    """
    sauce_names_with_size: set[str] = set()
    for r in rows:
        if r.food_name.strip().lower().startswith("sos") and r.size:
            sauce_names_with_size.add(r.food_name.strip().casefold())

    out: list[FoodRow] = []
    for r in rows:
        name_lower = r.food_name.strip().casefold()
        is_sauce = name_lower.startswith("sos")

        # Rule 1: drop unsized duplicate if sized version exists
        if is_sauce and not r.size and name_lower in sauce_names_with_size:
            print(f"  [Pasibus] dropping unsized sauce duplicate: {r.food_name}")
            continue

        # Rule 2: swap protein/fats if clearly reversed
        if is_sauce and not r.size and r.protein > r.fats:
            print(
                f"  [Pasibus] swapping protein/fats for {r.food_name}: "
                f"{r.protein}↔{r.fats}"
            )
            r = FoodRow(
                restaurant_name=r.restaurant_name,
                food_name=r.food_name,
                size=r.size,
                kcal=r.kcal,
                protein=r.fats,
                fats=r.protein,
                carbs=r.carbs,
            )

        out.append(r)
    return out


def _dedupe_food_rows(rows: list[FoodRow]) -> list[FoodRow]:
    seen: set[tuple] = set()
    out: list[FoodRow] = []
    for r in rows:
        size_key = (r.size or "").strip().casefold()
        key = (
            r.food_name.strip().casefold(),
            size_key,
            r.kcal,
            r.protein,
            r.fats,
            r.carbs,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _extract_pasibus_openai(
    row: dict, client: OpenAI, prompt: str
) -> RestaurantExtraction:
    """Two-page JPG scan: one structured parse per page so page 1 is not drowned out."""

    pasibus_rules = """


Pasibus (scanned JPG→PDF — no selectable text):
- Each request attaches exactly ONE image: that image is ONE full PDF page, in order.
- Extract EVERY menu item where you can read numeric kcal, protein (Białko), fats (Tłuszcz), and carbs (Węgle).
- Do not skip the top or margin of the page; small text still counts.
- Use size when the table shows a portion name (e.g. burger vs podwójny); else null.
- restaurant_name must be exactly: Pasibus
"""

    pdf_bytes = fetch_bytes(row["Macro table link"])
    page_pngs = pasibus_pdf_bytes_to_png_data_urls(pdf_bytes)

    if not page_pngs:
        fallback_prompt = (
            prompt
            + pasibus_rules
            + "\n\n(Raster failed — fallback PDF attachment.) Read BOTH pages.\n"
        )
        resp = client.responses.parse(
            model="gpt-5.4",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": fallback_prompt},
                        {"type": "input_file", "file_url": row["Macro table link"]},
                    ],
                },
            ],
            text_format=RestaurantExtraction,
        )
        if resp.output_parsed is None:
            raise RuntimeError("Empty response.output_parsed")
        return resp.output_parsed

    combined: list[FoodRow] = []
    total_pages = len(page_pngs)

    for idx, image_url in enumerate(page_pngs):
        page_scope = (
            f"\n\n=== PASIBUS SCAN — IMAGE {idx + 1} OF {total_pages} ONLY ===\n"
            "Extract only rows visibly printed on THIS image. "
            "If a row spans images, attach it to the image where its numbers appear.\n"
        )
        resp = client.responses.parse(
            model="gpt-5.4",
            max_output_tokens=16384,
            input=[
                {  # type: ignore[list-item,misc]
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt + pasibus_rules + page_scope,
                        },
                        {"type": "input_image", "image_url": image_url},
                    ],
                },
            ],
            text_format=RestaurantExtraction,
        )
        part = resp.output_parsed
        if part is None:
            raw_text = getattr(resp, "output_text", None) or "(no raw text)"
            print(
                f"  [Pasibus] WARNING: output_parsed is None on image "
                f"{idx + 1}/{total_pages}. Raw output snippet: {raw_text[:300]}"
            )
            continue
        print(
            f"  [Pasibus] image {idx + 1}/{total_pages}: extracted {len(part.foods)} foods"
        )
        combined.extend(part.foods)

    if not combined:
        raise RuntimeError("Pasibus: no foods extracted from any page image")
    cleaned = _fix_pasibus_sauces(combined)
    return RestaurantExtraction(
        restaurant_name="Pasibus",
        foods=_dedupe_food_rows(cleaned),
    )


def pasibus_pdf_bytes_to_png_data_urls(
    pdf_bytes: bytes,
    *,
    dpi_res: int = 300,
) -> list[str] | None:
    """Rasterize each PDF page — Pasibus JPG→PDF has no text layer; URL-only ingest skips page 1."""
    try:
        import pdfplumber  # optional; aligns with project's [extract] extra
    except ImportError:
        return None

    urls: list[str] = []
    buffer = io.BytesIO(pdf_bytes)
    try:
        with pdfplumber.open(buffer) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                pil = page.to_image(resolution=dpi_res)
                img = pil.original
                w, h = img.size

                # Portrait / dense pages: split into 3 overlapping vertical strips
                if h > w:
                    strips = [
                        (0, int(0.40 * h)),
                        (int(0.30 * h), int(0.70 * h)),
                        (int(0.60 * h), h),
                    ]
                    print(
                        f"  [Pasibus] page {page_num}: portrait {w}x{h}, splitting into {len(strips)} strips"
                    )
                    for s_idx, (y0, y1) in enumerate(strips):
                        cropped = img.crop((0, y0, w, y1))
                        out = io.BytesIO()
                        cropped.save(out, format="PNG", optimize=True)
                        b64 = base64.standard_b64encode(out.getvalue()).decode("ascii")
                        urls.append(f"data:image/png;base64,{b64}")
                        print(f"    strip {s_idx + 1}: rows {y0}–{y1}")
                else:
                    print(
                        f"  [Pasibus] page {page_num}: landscape {w}x{h}, keeping as-is"
                    )
                    out = io.BytesIO()
                    img.save(out, format="PNG", optimize=True)
                    b64 = base64.standard_b64encode(out.getvalue()).decode("ascii")
                    urls.append(f"data:image/png;base64,{b64}")
    except Exception:
        return None
    return urls if urls else None


root = Path(__file__).resolve().parents[2]
sources = Path(root / "data" / "sources.csv").resolve()


def get_openai_client() -> OpenAI:
    key = os.environ.get("OPENAI_SECRET_KEY")
    if not key:
        raise RuntimeError(
            "OPENAI_SECRET_KEY is not set. Add it to .env or the environment, "
            "or run without --use-openai / MACRO_USE_OPENAI."
        )
    return OpenAI(api_key=key)


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


def extract_restaurant_openai(row: dict, client: OpenAI) -> RestaurantExtraction:
    prompt = build_prompt(name=row["Name"], notes=row.get("Notes", "") or "")
    fmt = (row.get("Macro table format") or "").strip().lower()
    response = None

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
        return _extract_pasibus_openai(row, client, prompt)
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
    elif fmt == "pdf":
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
            f"OpenAI extractor: unsupported row {row['Name']} ({row.get('Macro table format')})"
        )

    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("Empty response.output_parsed")
    return parsed


def main() -> None:
    load_dotenv()
    from app.extract_macros import run  # noqa: PLC0415

    print(
        "Note: Prefer `PYTHONPATH=src python -m app.extract_macros "
        "--use-openai --no-merge` for explicit control."
    )
    run(
        use_openai=True,
        merge=False,
        only=None,
        sources_path=sources,
        out_path=root / "data" / "macros.csv",
    )


if __name__ == "__main__":
    main()
