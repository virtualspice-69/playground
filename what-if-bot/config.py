"""Loads and validates bot configuration from environment variables (.env)."""

import os
import sys

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


BOT_TOKEN = _get("BOT_TOKEN")
TOKEN_CONTRACT_ADDRESS = _get("TOKEN_CONTRACT_ADDRESS")
DEXSCREENER_PAIR_ADDRESS = _get("DEXSCREENER_PAIR_ADDRESS")

TOKEN_TICKER = _get("TOKEN_TICKER", "IF")
TOKEN_NAME = _get("TOKEN_NAME", "What If")

WEBSITE_URL = _get("WEBSITE_URL")
TWITTER_URL = _get("TWITTER_URL")
TELEGRAM_GROUP_URL = _get("TELEGRAM_GROUP_URL")
UNISWAP_BUY_URL = _get("UNISWAP_BUY_URL")
BLOFIN_URL = _get("BLOFIN_URL")

IMAGE_GEN_PROVIDER = _get("IMAGE_GEN_PROVIDER", "pollinations")

# FLUX is the current best-in-class open-weights image model and is what
# Pollinations serves by default — noticeably better anatomy, hands and text
# rendering than the older SDXL-class models. "turbo" is faster but lower
# fidelity; keep "flux" for final art.
IMAGE_GEN_MODEL = _get("IMAGE_GEN_MODEL", "flux")

# Describes $IF — the mascot — so every AI generation stays on-brand and
# consistent. The wording is deliberately specific about anatomy, finish and
# lighting, because vague prompts are the #1 cause of a character drifting
# between generations. Override in .env once a look is locked in.
CHARACTER_PROMPT = _get(
    "CHARACTER_PROMPT",
    "$IF, a single male cosmic entity: completely bald and hairless with no eyebrows, "
    "smooth polished emerald green skin with a glossy metallic sheen and bright "
    "specular highlights, lean powerful anatomically defined musculature, strong "
    "angular jaw, heavy brow, piercing glowing white eyes, calm and menacing "
    "expression, solo character, "
    "comic book illustration with bold confident inked linework, cel shaded with "
    "deep black shadows, high contrast, vivid saturated color, rim lighting in "
    "neon green, cinematic composition, masterpiece quality",
)

# Appended to every prompt to steer the model away from common failure modes.
NEGATIVE_PROMPT = _get(
    "NEGATIVE_PROMPT",
    "hair, beard, eyebrows, multiple characters, sidekick, extra people, crowd, "
    "deformed hands, extra fingers, extra limbs, mutated anatomy, blurry, "
    "low contrast, washed out, dull colors, watermark, signature, text artifacts, "
    "ugly, amateur",
)

IMAGE_GEN_STYLE_SUFFIX = _get(
    "IMAGE_GEN_STYLE_SUFFIX",
    ", crypto meme art style, vibrant colors, bold clean linework, high detail, trending",
)

COMMAND_COOLDOWN_SECONDS = float(_get("COMMAND_COOLDOWN_SECONDS", "8"))

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "templates")
FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
MANIFEST_PATH = os.path.join(ASSETS_DIR, "manifest.json")


def require_bot_token() -> str:
    if not BOT_TOKEN:
        sys.exit(
            "BOT_TOKEN is not set. Copy .env.example to .env and paste the token "
            "you got from @BotFather on Telegram."
        )
    return BOT_TOKEN
