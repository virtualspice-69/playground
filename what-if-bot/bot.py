"""Entrypoint for the $IF Telegram bot. Run with: python bot.py"""

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

import config
from handlers import art, library, meme, price, start

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)


def build_application() -> Application:
    token = config.require_bot_token()
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start.start))
    application.add_handler(CommandHandler("help", start.help_command))
    application.add_handler(CommandHandler("links", start.links_command))
    application.add_handler(CommandHandler("buy", start.buy_command))

    application.add_handler(CommandHandler("price", price.price_command))
    application.add_handler(CommandHandler("chart", price.price_command))

    application.add_handler(CommandHandler("meme", meme.meme_command))

    application.add_handler(CommandHandler("art", art.art_command))
    application.add_handler(CommandHandler("variations", art.variations_command))
    application.add_handler(CallbackQueryHandler(art.variation_button, pattern=r"^variation:"))

    application.add_handler(CommandHandler("random", library.random_command))
    application.add_handler(CommandHandler("gif", library.gif_command))

    return application


def main() -> None:
    application = build_application()
    logging.info("Starting %s bot...", config.TOKEN_NAME)
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
