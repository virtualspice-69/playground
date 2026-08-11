#!/usr/bin/env python3
"""Generates the $IF Studio launcher icon at every density.

Mark: a glowing green "$IF" wordmark on near-black, matching the studio UI.
"""

import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BG = (7, 10, 7)
ACC = (74, 222, 128)

DENSITIES = {
    "mdpi": 48,
    "hdpi": 72,
    "xhdpi": 96,
    "xxhdpi": 144,
    "xxxhdpi": 192,
}

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def font_at(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render(px):
    # Supersample 4x, then downscale — keeps the curves clean at 48px.
    s = px * 4
    img = Image.new("RGB", (s, s), BG)
    d = ImageDraw.Draw(img)

    # Soft radial glow behind the mark.
    glow = Image.new("RGB", (s, s), BG)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([s * 0.12, s * 0.12, s * 0.88, s * 0.88], fill=(18, 52, 30))
    glow = glow.filter(ImageFilter.GaussianBlur(s * 0.09))
    img = Image.blend(img, glow, 0.85)
    d = ImageDraw.Draw(img)

    # Rounded border ring.
    inset = s * 0.06
    d.rounded_rectangle(
        [inset, inset, s - inset, s - inset],
        radius=s * 0.22,
        outline=(32, 74, 48),
        width=max(2, int(s * 0.016)),
    )

    text = "$IF"
    f = font_at(int(s * 0.40))
    box = d.textbbox((0, 0), text, font=f)
    d.text(
        ((s - (box[2] - box[0])) / 2 - box[0], (s - (box[3] - box[1])) / 2 - box[1]),
        text,
        font=f,
        fill=ACC,
    )

    return img.resize((px, px), Image.LANCZOS)


def main():
    for name, px in DENSITIES.items():
        out_dir = os.path.join(HERE, "res", "mipmap-" + name)
        os.makedirs(out_dir, exist_ok=True)
        render(px).save(os.path.join(out_dir, "ic_launcher.png"))
        print("mipmap-%s/ic_launcher.png (%dpx)" % (name, px))


if __name__ == "__main__":
    main()
