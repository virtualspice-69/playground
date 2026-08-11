from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import config

HELP_TEXT = (
    f"*{config.TOKEN_NAME} (${config.TOKEN_TICKER}) Bot*\n\n"
    "*/price* — live price, liquidity, market cap\n"
    "*/meme* `top text | bottom text` — put text on a random meme template "
    "(reply to a photo with /meme to use that image instead)\n"
    "*/variations* — pick a preset $IF Guy scene and get a fresh AI-generated take on it\n"
    "*/art* `your prompt` — AI-generate custom $IF-branded art from a description\n"
    "*/random* — a random piece from the community art library\n"
    "*/gif* — a random animated piece from the library\n"
    "*/buy* — where to buy $IF\n"
    "*/links* — website, X, Telegram\n"
)


def _links_keyboard() -> InlineKeyboardMarkup | None:
    buttons = []
    if config.WEBSITE_URL:
        buttons.append(InlineKeyboardButton("🌐 Website", url=config.WEBSITE_URL))
    if config.TWITTER_URL:
        buttons.append(InlineKeyboardButton("𝕏 Twitter", url=config.TWITTER_URL))
    if config.TELEGRAM_GROUP_URL:
        buttons.append(InlineKeyboardButton("💬 Telegram", url=config.TELEGRAM_GROUP_URL))
    if config.UNISWAP_BUY_URL:
        buttons.append(InlineKeyboardButton("🦄 Buy on Uniswap", url=config.UNISWAP_BUY_URL))
    if config.BLOFIN_URL:
        buttons.append(InlineKeyboardButton("Buy on BloFin", url=config.BLOFIN_URL))
    if not buttons:
        return None
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        HELP_TEXT, parse_mode="Markdown", reply_markup=_links_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def links_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = _links_keyboard()
    if not keyboard:
        await update.message.reply_text(
            "No links configured yet — set WEBSITE_URL / TWITTER_URL / "
            "TELEGRAM_GROUP_URL in .env."
        )
        return
    await update.message.reply_text(f"*{config.TOKEN_NAME}* links:", parse_mode="Markdown", reply_markup=keyboard)


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    buttons = []
    if config.UNISWAP_BUY_URL:
        buttons.append(InlineKeyboardButton("🦄 Uniswap", url=config.UNISWAP_BUY_URL))
    if config.BLOFIN_URL:
        buttons.append(InlineKeyboardButton("BloFin", url=config.BLOFIN_URL))

    if not buttons:
        await update.message.reply_text(
            "No buy links configured yet — set UNISWAP_BUY_URL / BLOFIN_URL in .env."
        )
        return

    await update.message.reply_text(
        f"Buy *${config.TOKEN_TICKER}*:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([buttons]),
    )
