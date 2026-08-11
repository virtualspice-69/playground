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

# Describes the "$IF Guy" mascot so every AI generation stays on-brand:
# tall, bald, green-skinned, muscular, dark/neon-green crypto-meme aesthetic.
# Override in .env once you've locked in a look you like from testing.
CHARACTER_PROMPT = _get(
    "CHARACTER_PROMPT",
    "a tall bald hairless green-skinned muscular humanoid man with a strong jaw and "
    "intense narrow eyes, iconic crypto mascot character, dark moody atmosphere with "
    "glowing neon green accents, crypto meme culture aesthetic, extremely detailed "
    "illustration, sharp focus, dramatic lighting",
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
