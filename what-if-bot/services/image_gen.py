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

# Ready-made scenes featuring the $IF mascot, all built on config.CHARACTER_PROMPT
# so the character stays consistent. Used by /variations and as inspiration for
# freeform /art prompts. Add more here as the community/art direction evolves.
PRESET_SCENES: dict[str, str] = {
    "moon": "planting a green flag with a glowing dollar sign IF emblem on the surface of the moon, earth visible in the starry sky behind him, epic wide shot",
    "gold_mountain": "standing triumphantly atop a mountain of glowing gold coins during a lightning storm, holding a tattered green flag with a dollar sign IF emblem, cinematic comic book cover art style",
    "private_jet": "wearing a sleek black suit smoking a cigar in the cockpit of a private jet, city skyline glowing through the window at night, hyper detailed digital painting",
    "cosmic_flight": "muscular superhero physique with a flowing green cape and glowing dollar sign IF chest emblem, flying through a swirling green cosmic nebula alongside a small frog sidekick in a ninja hood, vibrant anime illustration style",
    "boxing_ring": "as a boxer in a neon lit boxing ring throwing a punch, dollar sign IF printed on shorts, roaring crowd in the background, dynamic action comic art style",
    "trading_floor": "standing behind a chaotic trading desk covered in monitors showing green candlestick charts, calm confident expression, neon city lights through the window, cinematic digital painting",
    "mob_boss": "in a white dress shirt and dark tie holding a vintage red telephone to his ear, smoking a cigar, city skyline visible through a window at night, moody cinematic anime illustration style",
}


class ImageGenError(RuntimeError):
    pass


def build_character_prompt(scene: str) -> str:
    """Combines the mascot description with a scene so the character stays
    consistent across generations, e.g. build_character_prompt(PRESET_SCENES["moon"])."""
    return f"{config.CHARACTER_PROMPT}, {scene}"


async def generate_image(prompt: str, *, width: int = 1024, height: int = 1024) -> bytes:
    if config.IMAGE_GEN_PROVIDER != "pollinations":
        raise ImageGenError(f"Unknown IMAGE_GEN_PROVIDER: {config.IMAGE_GEN_PROVIDER!r}")

    full_prompt = f"{prompt}{config.IMAGE_GEN_STYLE_SUFFIX}"
    encoded = urllib.parse.quote(full_prompt)
    seed = random.randint(0, 2**31 - 1)
    url = POLLINATIONS_URL.format(prompt=encoded)

    params = {
        "width": width,
        "height": height,
        "seed": seed,
        "nologo": "true",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            raise ImageGenError(f"Image generation failed (HTTP {resp.status_code})")
        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type:
            raise ImageGenError("Image generation service returned a non-image response")
        return resp.content
