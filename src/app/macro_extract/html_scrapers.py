from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.macro_extract.http_util import fetch_text
from app.macro_schema import FoodRow

_RE_NUMBER = re.compile(r"(-?\d+(?:[,.]\d+)?)")


def _first_float(raw: str) -> float:
    m = _RE_NUMBER.search(raw.replace(" ", ""))
    if not m:
        raise ValueError(f"no number in {raw!r}")
    return float(m.group(1).replace(",", "."))


def _strip_g(val: str) -> float:
    return _first_float(val.replace("g", ""))


def _hulthai_macro_header_cells(cells: list[str]) -> bool:
    u = " ".join(c.strip().upper() for c in cells)
    return "WARTOŚCI" in u and "KCAL" in u and ("WĘGL" in u or "BIAŁ" in u)


def _hulthai_dish_title_near_table(table) -> str:
    parent = table
    for _ in range(20):
        parent = getattr(parent, "parent", None)
        if parent is None:
            break
        h3 = parent.select_one("h3.uagb-ifb-title")
        if h3:
            return str(h3.get_text(strip=True))
    return ""


def parse_hulthai_html(html: str, restaurant_name: str = "HulThai") -> list[FoodRow]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[FoodRow] = []

    for table in soup.find_all("table"):
        thead = table.find("thead")
        tbody = table.find("tbody")
        data_trs: list = []
        if thead and tbody:
            hr = thead.find("tr")
            if not hr:
                continue
            hdr = [c.get_text(strip=True) for c in hr.find_all(["th", "td"])]
            if not _hulthai_macro_header_cells(hdr):
                continue
            data_trs = tbody.find_all("tr")
            tfoot = table.find("tfoot")
            if tfoot:
                data_trs = list(data_trs) + tfoot.find_all("tr")
        elif tbody:
            all_tr = tbody.find_all("tr")
            if not all_tr:
                continue
            hdr = [c.get_text(strip=True) for c in all_tr[0].find_all(["td", "th"])]
            if not _hulthai_macro_header_cells(hdr):
                continue
            data_trs = all_tr[1:]
        else:
            continue

        dish_title = _hulthai_dish_title_near_table(table)

        for tr in data_trs:
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) < 5 or _hulthai_macro_header_cells(cells):
                continue
            variant = cells[0]
            base_name = f"{dish_title} — {variant}" if dish_title else variant
            try:
                rows.append(
                    FoodRow(
                        restaurant_name=restaurant_name,
                        food_name=base_name,
                        size=None,
                        kcal=float(_first_float(cells[1])),
                        protein=_strip_g(cells[2]),
                        fats=_strip_g(cells[3]),
                        carbs=_strip_g(cells[4]),
                    )
                )
            except ValueError:
                continue

    seen: set[tuple[str, str | None, float]] = set()
    unique: list[FoodRow] = []
    for r in rows:
        key = (r.food_name, r.size, r.kcal)
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique


def parse_max_html(html: str, restaurant_name: str = "MAX Burgers") -> list[FoodRow]:
    soup = BeautifulSoup(html, "html.parser")
    panes = soup.select("div#perServing.tab-pane.active")
    if not panes:
        panes = soup.select("div#perServing")

    rows: list[FoodRow] = []
    seen_name_kcal: set[tuple[str, float]] = set()

    for pane in panes:
        table = pane.find("table")
        if not table:
            continue
        tbody = table.find("tbody")
        if not tbody:
            continue

        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) != 9:
                continue
            texts = [td.get_text(strip=True) for td in tds]
            name = texts[0]
            try:
                wt = _first_float(texts[1])
                if wt <= 0:
                    continue
                kcal = _first_float(texts[3])
                fats = _first_float(texts[4].split()[0])
                carbs = _first_float(texts[5].split()[0])
                protein = _first_float(texts[6])
            except (ValueError, IndexError):
                continue
            key = (name.strip(), kcal)
            if key in seen_name_kcal:
                continue
            seen_name_kcal.add(key)
            size_s = f"{wt:g} g"
            rows.append(
                FoodRow(
                    restaurant_name=restaurant_name,
                    food_name=name,
                    size=size_s,
                    kcal=kcal,
                    protein=protein,
                    fats=fats,
                    carbs=carbs,
                )
            )
    return rows


_LUCA_SKIP_HREFS = frozenset(
    {
        "/products",
        "/produkty",
        "/locations",
        "/news",
        "/careers",
        "/homepage",
        "/custom-orders",
        "/favicon.ico",
        "/zmeu-coffee",
        "/zmeu",
        "/piekarnie",
        "/aktualnosci",
        "/kariera",
        "/historia-luca",
        "/parerea-ta-conteaza",
    }
)


def discover_luca_product_urls(
    listing_html: str,
    base: str = "https://lucabakery.pl",
) -> list[str]:
    soup = BeautifulSoup(listing_html, "html.parser")
    found: set[str] = set()
    for a in soup.find_all("a", href=True):
        h = str(a["href"]).strip()
        if not h.startswith("/") or "?" in h or h in _LUCA_SKIP_HREFS:
            continue
        if len(h) < 2 or h.startswith("//"):
            continue
        if "." in h.split("/")[-1] and any(
            h.lower().endswith(ext) for ext in (".jpg", ".png", ".svg", ".webp")
        ):
            continue
        if h.count("/") != 1:
            continue
        found.add(urljoin(base, h))
    return sorted(found)


def _luca_normalize_portion_label(label: str) -> str:
    k = label.strip().lower().rstrip(".").strip()
    if k in {"kawałek", "kawałki"}:
        return "slice"
    return label.strip()


def _luca_portion_labels_grams(waga_val: str) -> list[tuple[str, float]]:
    """Parse LUCA weight lines like «140 g / 1100 g»."""
    waga_val = waga_val.replace("\xa0", " ").strip()
    slash_pair = re.fullmatch(
        r"(\d+(?:[,.]\d+)?)\s*g\.?\s*/\s*(\d+(?:[,.]\d+)?)\s*g\.?",
        waga_val,
        flags=re.I,
    )
    if slash_pair:
        lo = float(slash_pair.group(1).replace(",", "."))
        hi = float(slash_pair.group(2).replace(",", "."))
        a, b = (lo, hi) if lo <= hi else (hi, lo)
        if b >= a * 3 and b >= 400:
            return [("slice", a), ("whole pizza", b)]
        return [("portion", a), ("portion", b)]
    chunks = [
        c.strip().strip(".").strip()
        for c in re.split(r"\s*\|\s*", waga_val)
        if c.strip()
    ]
    out: list[tuple[str, float]] = []
    for part in chunks:
        m = re.search(
            r"(.+?)\s+-\s+(\d+(?:[,.]\d+)?)\s*g\.?\s*$",
            part,
            flags=re.I,
        )
        if m:
            label = m.group(1).strip().strip("-–—").strip()
            grams = float(m.group(2).replace(",", "."))
            out.append((label, grams))
            continue
        m = re.search(
            r"(.+?)\s+(\d+(?:[,.]\d+)?)\s*g\.?\s*$",
            part,
            flags=re.I,
        )
        if m:
            label = m.group(1).strip().strip("-–—").strip()
            grams = float(m.group(2).replace(",", "."))
            out.append((label, grams))
    if out:
        return out
    m = re.search(r"(\d+(?:[,.]\d+)?)\s*g", waga_val, flags=re.I)
    if m:
        return [("porcja", float(m.group(1).replace(",", ".")))]
    return []


def _luca_value_after_anchor(block: str, anchor: re.Pattern[str]) -> float | None:
    """First quantity after anchor: supports «Kcal … - 247 |» and «254TŁUSZCZE»."""
    m = anchor.search(block)
    if not m:
        return None
    tail = block[m.end() : m.end() + 520]
    dash = re.search(r"-\s*(\d+(?:[,.]\d+)?)", tail)
    if dash:
        return float(dash.group(1).replace(",", "."))
    num = re.search(r"(\d+(?:[,.]\d+)?)", tail)
    if not num:
        return None
    return float(num.group(1).replace(",", "."))


def _luca_page_food_title(soup: BeautifulSoup) -> str:
    title = soup.find("title")
    raw = title.get_text(strip=True) if title else "Unknown"
    raw = re.split(r"\s*[|•]\s*", raw, maxsplit=1)[0].strip()
    return raw


def parse_luca_product_html(html: str, restaurant_name: str = "LUCA") -> list[FoodRow]:
    soup = BeautifulSoup(html, "html.parser")
    food_name = _luca_page_food_title(soup)

    waga_val: str | None = None
    nutr_lines: list[str] = []

    for row in soup.select("div.flex"):
        labels = row.select("p.text-white")
        values = row.select("p.text-grey-luca1")
        if len(labels) != 1 or len(values) != 1:
            continue
        lk = labels[0].get_text(strip=True).lower()
        val = values[0].get_text(" ", strip=True)
        if "weight" in lk or lk.startswith("masa") or lk.startswith("waga"):
            waga_val = val
        nutritionish = (
            "nutrition" in lk
            or "odżywcz" in lk
            or "wartości" in lk
            or "wartość" in lk
            or ("informacja" in lk and "100" in lk)
        )
        if nutritionish and "100" in lk and "g" in lk:
            nutr_lines = [ln.strip() for ln in val.splitlines() if ln.strip()]

    portions = _luca_portion_labels_grams(waga_val or "")
    if not portions or not nutr_lines:
        return []

    block = "\n".join(nutr_lines)
    # Polish pages first — avoids English «kcal» matching
    # only whitespace before «Pizza».
    k100 = _luca_value_after_anchor(block, re.compile(r"energetyczna\s+kcal", re.I))
    if k100 is None:
        k100 = _luca_value_after_anchor(block, re.compile(r"\bkcal\b", re.I))
    f100 = _luca_value_after_anchor(block, re.compile(r"\btłuszcz(?:e)?\b", re.I))
    if f100 is None:
        f100 = _luca_value_after_anchor(block, re.compile(r"\bfats\b", re.I))
    c100 = _luca_value_after_anchor(block, re.compile(r"\bwęglowodany\b", re.I))
    if c100 is None:
        c100 = _luca_value_after_anchor(block, re.compile(r"\bcarbohydrates\b", re.I))
    p100 = _luca_value_after_anchor(block, re.compile(r"\bbiałk[oa]\b", re.I))
    if p100 is None:
        p100 = _luca_value_after_anchor(block, re.compile(r"\bproteins\b", re.I))

    if None in (k100, f100, c100, p100):
        return []
    assert k100 is not None
    assert p100 is not None
    assert f100 is not None
    assert c100 is not None

    factor_base = 1.0 / 100.0
    rows: list[FoodRow] = []
    for plabel, grams in portions:
        factor = grams * factor_base
        suffix = _luca_normalize_portion_label(plabel) if plabel != "porcja" else ""
        fname = f"{food_name} ({suffix})" if suffix else food_name
        rows.append(
            FoodRow(
                restaurant_name=restaurant_name,
                food_name=fname.strip(),
                size=f"{grams:g} g",
                kcal=round(k100 * factor, 2),
                protein=round(p100 * factor, 2),
                fats=round(f100 * factor, 2),
                carbs=round(c100 * factor, 2),
            )
        )
    return rows


def fetch_and_parse_hulthai(url: str) -> list[FoodRow]:
    return parse_hulthai_html(fetch_text(url))


def fetch_and_parse_max(url: str) -> list[FoodRow]:
    return parse_max_html(fetch_text(url))


_LUCA_POLISH_CHARS = frozenset("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")


def _luca_food_fingerprint(fr: FoodRow) -> tuple:
    """One row per portion/macros tuple (dedup PL vs EN)."""
    return (
        round(fr.kcal, 4),
        round(fr.protein, 4),
        round(fr.fats, 4),
        round(fr.carbs, 4),
        (fr.size or "").strip(),
    )


def dedupe_luca_food_rows(rows: list[FoodRow]) -> list[FoodRow]:
    """Prefer English titles when rows share same macros."""

    def title_pref_key(name: str) -> tuple[int, float, str]:
        n = name.replace("®", "").replace("™", "").replace("(R)", "").strip()
        pol = sum(1 for c in n if c in _LUCA_POLISH_CHARS)
        ascii_frac = sum(1 for c in n if ord(c) < 128) / max(len(n), 1) if n else 0
        # Sort key: fewer PL letters, richer ASCII ratio, stabler lexical tie-breaking.
        return (pol, -ascii_frac, name.casefold())

    buckets: dict[tuple, FoodRow] = {}
    for r in rows:
        k = _luca_food_fingerprint(r)
        prev = buckets.get(k)
        if prev is None or title_pref_key(r.food_name) < title_pref_key(prev.food_name):
            buckets[k] = r
    return sorted(buckets.values(), key=lambda x: x.food_name.casefold())


def fetch_and_parse_luca_catalog(
    listing_url: str,
    *,
    max_products: int | None = 80,
) -> list[FoodRow]:
    """Discover from English /products (PL slugs duplicate)."""
    urls: set[str] = set()
    try:
        urls.update(
            discover_luca_product_urls(fetch_text("https://lucabakery.pl/products"))
        )
    except Exception:
        pass
    extra = (listing_url or "").strip()
    if extra and extra not in {
        "https://lucabakery.pl/produkty",
        "https://lucabakery.pl/products",
    }:
        try:
            urls.update(discover_luca_product_urls(fetch_text(extra)))
        except Exception:
            pass
    urls_ordered = sorted(urls)
    rows: list[FoodRow] = []
    for i, u in enumerate(urls_ordered):
        if max_products is not None and i >= max_products:
            break
        try:
            html = fetch_text(u)
        except Exception:
            continue
        try:
            rows.extend(parse_luca_product_html(html))
        except Exception:
            continue
    rows = dedupe_luca_food_rows(rows)
    rows = _luca_append_combo_sum_rows(rows)
    return rows


def _luca_append_combo_sum_rows(rows: list[FoodRow]) -> list[FoodRow]:
    """Approximate combo nutrition from standalone items."""
    nut = next(
        (r for r in rows if r.food_name.strip().casefold() == "pretzel with nutella"),
        None,
    )
    slice_campus = next(
        (
            r
            for r in rows
            if "pizza campus" in r.food_name.casefold()
            and "(slice)" in r.food_name.casefold()
        ),
        None,
    )
    if nut is None or slice_campus is None:
        return rows
    combo = FoodRow(
        restaurant_name="LUCA",
        food_name="Combo (Nutella pretzel + Pizza Campus slice)",
        size=None,
        kcal=round(nut.kcal + slice_campus.kcal, 2),
        protein=round(nut.protein + slice_campus.protein, 2),
        fats=round(nut.fats + slice_campus.fats, 2),
        carbs=round(nut.carbs + slice_campus.carbs, 2),
    )
    return [*rows, combo]
