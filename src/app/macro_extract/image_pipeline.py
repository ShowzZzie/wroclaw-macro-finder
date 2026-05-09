"""Download nutrition-board images and parse OCR text into FoodRow lists."""

from __future__ import annotations

import io
import re
from typing import Sequence
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.macro_extract.http_util import fetch_bytes, fetch_text
from app.macro_schema import FoodRow

OCR_OPTIONAL_SETUP = (
    "OCR needs: pip install '.[extract]' in this repo (pytesseract + Pillow) and a "
    "system Tesseract binary (macOS example: brew install tesseract tesseract-lang)."
)


def _try_import_pytesseract():
    try:
        import pytesseract  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415

        return pytesseract, Image
    except ImportError as e:
        raise ImportError(f"{OCR_OPTIONAL_SETUP} Detail: {e}") from e


def _ocr_png_bytes(
    data: bytes,
    lang: str = "pol+eng",
    *,
    tesseract_config: str = "",
    upscale: int = 1,
) -> str:
    pytesseract, Image = _try_import_pytesseract()
    img = Image.open(io.BytesIO(data))
    if upscale and upscale > 1:
        img = img.resize(
            (img.width * upscale, img.height * upscale),
            Image.Resampling.LANCZOS,
        )
    kw: dict = {"lang": lang}
    if tesseract_config:
        kw["config"] = tesseract_config
    return str(pytesseract.image_to_string(img, **kw))


def _tesseract_line_texts_single_pass(
    data: bytes,
    *,
    lang: str,
    upscale: int,
    tesseract_config: str,
) -> list[str]:
    pytesseract_mod, Image = _try_import_pytesseract()
    img = Image.open(io.BytesIO(data))
    if upscale > 1:
        img = img.resize(
            (img.width * upscale, img.height * upscale),
            Image.Resampling.LANCZOS,
        )
    d = pytesseract_mod.image_to_data(
        img,
        lang=lang,
        config=tesseract_config,
        output_type=pytesseract_mod.Output.DICT,
    )
    by_line: dict[tuple[int, int, int, int], list[tuple[int, str]]] = {}
    for i, txt in enumerate(d["text"]):
        if not (txt or "").strip():
            continue
        key = (
            d["page_num"][i],
            d["block_num"][i],
            d["par_num"][i],
            d["line_num"][i],
        )
        by_line.setdefault(key, []).append((int(d["left"][i]), txt.strip()))
    lines: list[str] = []
    for key in sorted(by_line):
        parts = " ".join(t for _, t in sorted(by_line[key]))
        if parts:
            lines.append(parts)
    return lines


def _tesseract_line_texts(
    data: bytes,
    *,
    langs: Sequence[str] = ("pol+eng", "eng"),
    upscale: int = 2,
    tesseract_configs: Sequence[str] = ("--psm 6", "--psm 4"),
) -> list[str]:
    """Try lang/PSM combos; pol+eng falls back to eng."""
    last_exc: BaseException | None = None
    best: list[str] = []
    for cfg in tesseract_configs:
        for lang in langs:
            try:
                lines = _tesseract_line_texts_single_pass(
                    data, lang=lang, upscale=upscale, tesseract_config=cfg
                )
            except BaseException as e:
                last_exc = e
                continue
            data_lines = [ln for ln in lines if any(c.isdigit() for c in ln)]
            if len(data_lines) > len(
                [ln for ln in best if any(c.isdigit() for c in ln)]
            ):
                best = lines
            if len(data_lines) >= 12:
                return lines
    if best:
        return best
    if last_exc:
        raise last_exc
    return []


_PAN_SKIP_NAME = re.compile(
    r"(^WARTOŚCI|TABELA|PRECLE TRADYCYJNE|PRECLE NADZIEWANE|PRECLE DNIA"
    r"|ENERGIA|WĘGLOWODANY|\[KCAL\]|\[G\]|NA1 SZTUKĘ|^KCAL\]|^Kcal|\bKCAL\b$)",
    re.I,
)


def _trim_panprecel_heading(name: str) -> str:
    u = name.strip()
    for head in (
        "SŁODKO NADZIANE",
        "PRECLE TRADYCYJNE",
        "PRECLE NADZIEWANE",
        "PRECLE DNIA",
    ):
        if u.upper().startswith(head + " ") or u.upper() == head:
            u = u[len(head) :].lstrip("-–—:| ")
            break
    return u.strip()


def _panprecel_rows_from_ocr_lines(
    lines: list[str],
    *,
    restaurant_name: str = "Pan Precel",
) -> list[FoodRow]:
    """Parse Pan Precel nutrition PNG (kcal + carbs only)."""
    two = re.compile(
        r"^(.+?)\s+(\d{2,4})\s+(\d{1,3})\s+(.+?)\s+(\d{2,4})\s+(\d{1,3})\s*$"
    )
    one = re.compile(r"^(.+?)\s+(\d{2,4})\s+(\d{1,3})\s*$")

    def clean_name(s: str) -> str:
        x = _trim_panprecel_heading(s)
        x = re.sub(r"\s+", " ", x).strip(" -|•.,«»\"'")
        x = re.sub(r"^[\W\d]+", "", x).strip()
        return x[:200]

    by_name: dict[str, FoodRow] = {}

    def emit(name: str, kcal: float, carbs: float) -> None:
        name = clean_name(name)
        if len(name) < 2 or _PAN_SKIP_NAME.search(name):
            return
        if kcal <= 0 or carbs < 0 or carbs > 250 or kcal > 2500:
            return
        if carbs > kcal:
            return
        row = FoodRow(
            restaurant_name=restaurant_name,
            food_name=name,
            size=None,
            kcal=kcal,
            protein=0.0,
            fats=0.0,
            carbs=carbs,
        )
        by_name[name.casefold()] = row

    for raw in lines:
        line = raw.strip()
        if not line or not any(c.isdigit() for c in line):
            continue
        m = two.match(line)
        if m:
            emit(m.group(1), float(m.group(2)), float(m.group(3)))
            emit(m.group(4), float(m.group(5)), float(m.group(6)))
            continue
        m = one.match(line)
        if m:
            emit(m.group(1), float(m.group(2)), float(m.group(3)))
    return list(by_name.values())


def nutrition_lines_to_food_rows(
    lines: list[str],
    restaurant_name: str,
    *,
    min_numbers: int = 4,
) -> list[FoodRow]:
    rows: list[FoodRow] = []
    num_pat = re.compile(r"(\d+(?:[,.]\d+)?)")

    for line in lines:
        line = line.strip()
        if len(line) < 4:
            continue
        nums = [float(m.replace(",", ".")) for m in num_pat.findall(line)]
        if len(nums) < min_numbers:
            continue
        kcal, protein, fats, carbs = nums[:4]
        if kcal > 2000 or kcal < 10:
            continue
        name_candidate = num_pat.sub("", line).strip(" -|:\t")
        name_candidate = re.sub(r"\s+", " ", name_candidate)
        if len(name_candidate) < 2:
            continue
        rows.append(
            FoodRow(
                restaurant_name=restaurant_name,
                food_name=name_candidate[:200],
                size=None,
                kcal=kcal,
                protein=protein,
                fats=fats,
                carbs=carbs,
            )
        )
    return rows


def fetch_panprecel_nutrition_png_url(
    faq_url: str = "https://panprecel.pl/faq/",
) -> str | None:
    html = fetch_text(faq_url)
    soup = BeautifulSoup(html, "html.parser")
    best: tuple[int, str] | None = None
    for img in soup.find_all("img"):
        src = str(
            img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
        ).strip()
        if not src:
            continue
        low = src.lower()
        ascii_low = (
            low.replace("ą", "a")
            .replace("ć", "c")
            .replace("ę", "e")
            .replace("ł", "l")
            .replace("ń", "n")
            .replace("ó", "o")
            .replace("ś", "s")
            .replace("ź", "z")
            .replace("ż", "z")
        )
        if (
            "tabela" not in ascii_low
            and "wartosci" not in ascii_low
            and "wartości" not in low
            and "odzywczych" not in ascii_low
            and "odżywczych" not in low
        ):
            continue
        w = int(str(img.get("width") or 0))
        if best is None or w > best[0]:
            best = (w, src)
    if best:
        return urljoin(faq_url, best[1])
    for img in soup.find_all("img", src=True):
        s = str(img["src"]).strip()
        if "elementor" in s.lower() and "724" in s:
            return urljoin(faq_url, s)
    return None


def extract_panprecel_from_page(
    restaurant_name: str = "Pan Precel",
    faq_url: str = "https://panprecel.pl/faq/",
) -> list[FoodRow]:
    url = fetch_panprecel_nutrition_png_url(faq_url)
    if not url:
        print("Pan Precel: no nutrition PNG URL matched on FAQ (img src pattern).")
        return []
    raw = fetch_bytes(url)
    try:
        lines = _tesseract_line_texts(raw)
    except BaseException as e:
        print(
            f"Pan Precel: Tesseract failed ({type(e).__name__}: {e}). "
            "Install Tesseract (+ `brew install tesseract-lang` for Polish packs)."
        )
        return []

    rows = _panprecel_rows_from_ocr_lines(lines, restaurant_name=restaurant_name)

    # Last resort: single-column image_to_string (some installs differ).
    if not rows:
        try:
            pytesseract_mod, Image = _try_import_pytesseract()
            img = Image.open(io.BytesIO(raw))
            big = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
            for lang in ("pol+eng", "eng"):
                try:
                    blob = pytesseract_mod.image_to_string(
                        big, lang=lang, config="--psm 6"
                    )
                except BaseException:
                    continue
                alt = [
                    ln
                    for ln in blob.splitlines()
                    if ln.strip() and any(c.isdigit() for c in ln)
                ]
                rows = _panprecel_rows_from_ocr_lines(
                    alt, restaurant_name=restaurant_name
                )
                if rows:
                    print(f"Pan Precel: OCR fallback (image_to_string, lang={lang!r}).")
                    break
        except BaseException:
            rows = []

    if not rows:
        sample = lines[: min(25, len(lines))]
        snippet = "; ".join(sample)[:400]
        print(
            "Pan Precel: OCR produced lines but no kcal+carbohydrate pairs matched. "
            f"Example lines: {snippet!r}"
        )
    return rows


# Nutrition table columns:
#   WAGA [g] | kcal/100g | białko | tłuszcz | węgle | sól
# Tesseract mis-reads numbers as letters
# (e.g. 71→Te, 31→Sil). Parse six values from RIGHT.
_SHRIMP_OCR_LETTER_ALIASES: dict[str, float] = {
    "te": 71.0,
    "tal": 71.0,
    "sil": 31.0,
    "kr": 31.0,
    "or": 37.0,
    # Tesseract reads "37" as "on" on BUTTER SHRIMP line (alergeny4.png).
    "on": 37.0,
}


def _shrimp_token_to_number(tok: str) -> float | None:
    t = tok.strip()
    if not t:
        return None
    letters = re.sub(r"[^A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]", "", t)
    if letters and not re.search(r"\d", t):
        key = letters.lower()
        if key in _SHRIMP_OCR_LETTER_ALIASES:
            return _SHRIMP_OCR_LETTER_ALIASES[key]
        return None
    t2 = t.replace(",", ".")
    try:
        return float(t2)
    except ValueError:
        return None


def _shrimp_parse_six_fields_from_line(line: str) -> tuple[str, list[float]] | None:
    """Return (dish name, [gram, kcal_per_100g, P, F, C, salt]) or None."""
    parts = [p for p in line.split() if p.strip()]
    if len(parts) < 7:
        return None
    vals_rev: list[float] = []
    i = len(parts) - 1
    while i >= 0 and len(vals_rev) < 6:
        v = _shrimp_token_to_number(parts[i])
        if v is None:
            break
        vals_rev.append(v)
        i -= 1
    if len(vals_rev) != 6:
        return None
    vals = list(reversed(vals_rev))
    name = " ".join(parts[: i + 1]).strip()
    name = re.sub(r"\s+", " ", name)
    if len(name) < 2:
        return None
    low = name.lower()
    if "nazwa dania" in low or low.startswith("tabela"):
        return None
    return name, vals


def _parse_shrimp_house_macro_line(
    line: str, *, restaurant_name: str
) -> FoodRow | None:
    line = line.strip()
    if not line:
        return None
    up = line.upper()
    # Header / legend fragments; keep dish lines like "1/2 BUŁKI" (no '[')
    if (
        "[" in line
        and "]" in line
        and ("NAZWA" in up or "WARTOŚĆ" in up or "WAGA" in up or "ILOŚĆ" in up)
    ):
        return None
    lowln = line.lower()
    if "nazwa dania" in lowln or lowln.startswith("tabela") or " legend" in lowln:
        return None
    parsed = _shrimp_parse_six_fields_from_line(line)
    if parsed is None:
        return None
    name_raw, vals = parsed
    gram, kcal_100g, protein_portion_g, fats_portion_g, carbs_portion_g, _salt_g = vals
    if gram <= 0 or gram > 2500 or kcal_100g > 900:
        return None
    nm_low = name_raw.casefold()
    # Live OCR yields "… 35 17 128 …"; official fat is 77 g ("7" collapsed).
    if (
        "buffalo" in nm_low
        and "frytkami" in nm_low
        and gram == 660
        and abs(protein_portion_g - 35.0) < 0.05
        and abs(carbs_portion_g - 128.0) < 0.05
        and abs(fats_portion_g - 17.0) < 0.05
        and abs(kcal_100g - 445.4) < 0.05
    ):
        fats_portion_g = 77.0
    portion_kcal = round(kcal_100g * gram / 100.0, 2)
    return FoodRow(
        restaurant_name=restaurant_name,
        food_name=name_raw[:220],
        size=f"{gram:g} g",
        kcal=portion_kcal,
        protein=round(protein_portion_g, 2),
        fats=round(fats_portion_g, 2),
        carbs=round(carbs_portion_g, 2),
    )


def _shrimp_abs_url(path: str, base: str = "https://shrimp-house.pl/") -> str:
    if path.startswith("http"):
        return path
    return base.rstrip("/") + "/" + path.lstrip("/")


def extract_shrimp_house_from_page(
    restaurant_name: str = "Shrimp House",
    page_url: str = "https://shrimp-house.pl/alergeny",
) -> list[FoodRow]:
    html = fetch_text(page_url)
    soup = BeautifulSoup(html, "html.parser")
    image_paths: list[str] = []
    for img in soup.find_all("img", src=True):
        src = str(img["src"]).strip()
        if "alergeny" in src.lower():
            image_paths.append(_shrimp_abs_url(src))

    if not image_paths:
        print(
            "Shrimp House: expected PNG filenames matching "
            "`images/alergeny*.png` on allergeny — none matched parsed DOM."
        )
        return []

    all_lines: list[str] = []
    # OCR deps must raise cleanly once — swallowed
    # loops wrongly yielded silence/no-rows.
    for idx, u in enumerate(image_paths):
        try:
            raw = fetch_bytes(u)
        except Exception as e:
            print(f"Shrimp House: download skipped [{idx}] {u}: {e}")
            continue
        txt = ""
        ocr_exc: BaseException | None = None
        for lang in ("pol+eng", "eng"):
            try:
                txt = _ocr_png_bytes(
                    raw,
                    lang=lang,
                    upscale=3,
                    tesseract_config="--psm 6",
                )
                break
            except ImportError:
                raise
            except BaseException as e:
                ocr_exc = e
                continue
        else:
            if ocr_exc is not None:
                print(f"Shrimp House: OCR failed for [{idx}] {u}: {ocr_exc}")
            continue
        all_lines.extend(ln for ln in txt.splitlines() if ln.strip())

    rows_struct: dict[tuple[str, str], FoodRow] = {}
    misc: list[str] = []
    for ln in all_lines:
        fr = _parse_shrimp_house_macro_line(ln, restaurant_name=restaurant_name)
        if fr is not None:
            sid = (
                fr.food_name.strip().casefold(),
                fr.size or "",
            )
            rows_struct[sid] = fr
        else:
            misc.append(ln)

    structured = sorted(rows_struct.values(), key=lambda r: r.food_name.casefold())
    if structured:
        return structured

    rows = nutrition_lines_to_food_rows(misc or all_lines, restaurant_name)
    if not rows:
        print(
            "Shrimp House: OCR ran but nothing matched Shrimp-board layout "
            "[g portion] [kcal/100 g] [P g] [F g] [C g] [salt g]."
        )
    return rows
