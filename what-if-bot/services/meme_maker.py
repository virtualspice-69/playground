"""Classic top/bottom text meme compositing over a template image, using Pillow.

This is the zero-cost path: no API calls, works on any image you drop into
assets/templates/. Text is auto-sized to fit the image width and wrapped
onto multiple lines if needed, with a black stroke for readability over any
background (the standard "meme font" look).
"""

from __future__ import annotations

import glob
import io
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

import config

_DEFAULT_FONT_CANDIDATES = ["Anton-Regular.ttf", "Impact.ttf", "impact.ttf", "DejaVuSans-Bold.ttf"]


class MemeError(RuntimeError):
    pass


def _find_font_path() -> str | None:
    for name in _DEFAULT_FONT_CANDIDATES:
        path = os.path.join(config.FONTS_DIR, name)
        if os.path.exists(path):
            return path
    # Fall back to any .ttf the user dropped into the fonts folder.
    matches = glob.glob(os.path.join(config.FONTS_DIR, "*.ttf"))
    return matches[0] if matches else None


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    path = _find_font_path()
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, font_path: str | None, start_size: int) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    size = start_size
    while size > 12:
        font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
        avg_char_w = font.getbbox("M")[2] or 1
        wrap_width = max(1, int(max_width / avg_char_w))
        lines = textwrap.wrap(text.upper(), width=wrap_width) or [""]
        widest = max(draw.textlength(line, font=font) for line in lines)
        if widest <= max_width:
            return font, lines
        size -= 4
    font = ImageFont.truetype(font_path, 12) if font_path else ImageFont.load_default()
    return font, textwrap.wrap(text.upper(), width=20) or [""]


def _draw_outlined_text(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, font, fill="white", stroke="black", stroke_width=4):
    x, y = xy
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke, anchor="ma")


def make_meme(image_bytes: bytes, top_text: str = "", bottom_text: str = "") -> bytes:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise MemeError(f"Could not read template image: {exc}") from exc

    draw = ImageDraw.Draw(img)
    font_path = _find_font_path()
    max_width = int(img.width * 0.92)
    start_size = max(24, img.height // 8)

    if top_text:
        font, lines = _fit_text(draw, top_text, max_width, font_path, start_size)
        y = img.height * 0.02
        line_height = font.getbbox("Mg")[3] + 6
        for line in lines:
            _draw_outlined_text(draw, (img.width / 2, y), line, font)
            y += line_height

    if bottom_text:
        font, lines = _fit_text(draw, bottom_text, max_width, font_path, start_size)
        line_height = font.getbbox("Mg")[3] + 6
        total_h = line_height * len(lines)
        y = img.height * 0.98 - total_h
        for line in lines:
            _draw_outlined_text(draw, (img.width / 2, y), line, font)
            y += line_height

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=92)
    return out.getvalue()
