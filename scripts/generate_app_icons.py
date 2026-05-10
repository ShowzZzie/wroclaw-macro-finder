"""Render the WMF favicon as PNG icons for iOS / Android home screens.

Mirrors frontend/public/favicon.svg: black square with a lime border and "MF".
Output goes to frontend/public/. Re-run whenever the SVG changes.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "frontend" / "public"

# Match favicon.svg
BG = (10, 10, 10, 255)  # #0a0a0a
LIME = (200, 238, 68, 255)  # #c8ee44

SIZES: dict[str, int] = {
    "apple-touch-icon.png": 180,  # iOS Safari "Add to Home Screen"
    "icon-192.png": 192,  # Android / generic
    "icon-512.png": 512,  # Android splash / large
}

FONT_CANDIDATES = [
    ("/System/Library/Fonts/Menlo.ttc", 1),  # Menlo Bold
    ("/System/Library/Fonts/Supplemental/Courier New Bold.ttf", 0),
    ("/Library/Fonts/Courier New Bold.ttf", 0),
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path, index in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size, index=index)
            except OSError:
                continue
    raise RuntimeError("No suitable monospace bold font found.")


def render(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(img)

    # SVG has a 1-unit inset and 2-unit stroke on a 32-unit canvas.
    inset = max(2, round(size * (1 / 32)))
    stroke = max(2, round(size * (2 / 32)))
    draw.rectangle(
        [inset, inset, size - inset - 1, size - inset - 1],
        outline=LIME,
        width=stroke,
    )

    # SVG font-size is 18 on a 32-unit canvas → ~56% of size. Bold mono
    # rasterises a touch wider than the original SVG glyph metrics, so
    # nudge slightly down for a comparable optical fit.
    font = load_font(round(size * 0.52))
    text = "MF"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) / 2 - bbox[0]
    ty = (size - th) / 2 - bbox[1]
    draw.text((tx, ty), text, fill=LIME, font=font)
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, size in SIZES.items():
        out = OUT_DIR / name
        render(size).save(out, "PNG", optimize=True)
        print(f"wrote {out.relative_to(ROOT)} ({size}x{size})")


if __name__ == "__main__":
    main()
