"""AI art generation.

Default provider is Pollinations.ai — free, no API key, no signup. It's a
public image-generation endpoint backed by open diffusion models. Good
enough for meme/community art and costs nothing per generation, which is
why it's the default here.

If you later want tighter style control or higher fidelity and are willing
to pay a small per-image cost, swap in Replicate/Together/Stability by
adding another branch below and pointing IMAGE_GEN_PROVIDER at it in .env.
"""

from __future__ import annotations

import random
import urllib.parse

import httpx

import config

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"

# Ready-made scenes featuring $IF, all built on config.CHARACTER_PROMPT so the
# character stays consistent. Used by /variations and as inspiration for
# freeform /art prompts. $IF always appears alone — no sidekicks.
PRESET_SCENES: dict[str, str] = {
    "portrait": "heroic head and shoulders portrait facing the viewer, deep space nebula and starfield behind him, dramatic rim lighting carving out his jaw and skull, intense glowing eyes, iconic character key art",
    "cosmic_surfer": "riding a sleek glowing board through deep space, body low and balanced in a dynamic surfing stance, trailing a comet tail of green energy, galaxies and starfields all around, epic full body wide shot",
    "moon": "planting a green flag bearing a glowing dollar sign IF emblem on the surface of the moon, earth hanging in the starry sky behind him, epic cinematic wide shot",
    "gold_mountain": "standing triumphantly atop a mountain of glowing gold coins during a lightning storm, holding a tattered flag with a glowing dollar sign IF emblem, comic book cover composition",
    "private_jet": "wearing a crisp white dress shirt and dark tie, smoking a cigar in the cabin of a private jet, city skyline glowing through the window at night",
    "boxing_ring": "as a boxer in a neon lit ring mid punch, dollar sign IF on his shorts, roaring crowd blurred behind him, dynamic action angle",
    "trading_floor": "standing before a wall of monitors showing surging green candlestick charts, arms folded, calm and unbothered, neon city lights through the window behind him",
    "mob_boss": "in a white dress shirt and dark tie holding a vintage red telephone to his ear, cigar smoke curling through the air, city skyline through the window at night",
    "throne": "seated on a massive obsidian throne carved with glowing green sigils, one hand resting on the armrest, monumental low angle shot, shafts of light from above",
}


class ImageGenError(RuntimeError):
    pass


def build_character_prompt(scene: str) -> str:
    """Combines the mascot description with a scene so the character stays
    consistent across generations, e.g. build_character_prompt(PRESET_SCENES["moon"])."""
    return f"{config.CHARACTER_PROMPT}, {scene}"


def build_url(prompt: str, *, width: int = 1024, height: int = 1024, seed: int | None = None) -> str:
    """Builds the full generation URL. Exposed separately so scripts/art_lab.py
    (and you, in a browser) can use the exact same pipeline the bot uses."""
    full_prompt = f"{prompt}{config.IMAGE_GEN_STYLE_SUFFIX}"
    if config.NEGATIVE_PROMPT:
        full_prompt = f"{full_prompt} | negative: {config.NEGATIVE_PROMPT}"

    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    params = urllib.parse.urlencode(
        {
            "width": width,
            "height": height,
            "seed": seed,
            "model": config.IMAGE_GEN_MODEL,
            "nologo": "true",
            "enhance": "true",
        }
    )
    encoded = urllib.parse.quote(full_prompt, safe="")
    return f"{POLLINATIONS_URL.format(prompt=encoded)}?{params}"


async def generate_image(
    prompt: str, *, width: int = 1024, height: int = 1024, seed: int | None = None
) -> bytes:
    if config.IMAGE_GEN_PROVIDER != "pollinations":
        raise ImageGenError(f"Unknown IMAGE_GEN_PROVIDER: {config.IMAGE_GEN_PROVIDER!r}")

    url = build_url(prompt, width=width, height=height, seed=seed)

    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise ImageGenError(f"Image generation failed (HTTP {resp.status_code})")
        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type:
            raise ImageGenError("Image generation service returned a non-image response")
        return resp.content
