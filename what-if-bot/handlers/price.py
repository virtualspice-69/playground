from telegram import Update
from telegram.ext import ContextTypes

from services import dexscreener


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("Fetching price...")
    try:
        info = await dexscreener.fetch_price()
    except dexscreener.DexScreenerError as exc:
        await msg.edit_text(f"Couldn't fetch price: {exc}")
        return
    except Exception:
        await msg.edit_text("Price lookup failed unexpectedly. Try again in a moment.")
        return

    await msg.edit_text(
        dexscreener.format_price_message(info),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
