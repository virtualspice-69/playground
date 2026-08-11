from telegram import Update
from telegram.ext import ContextTypes

from services import library, meme_maker


def _parse_text(raw: str) -> tuple[str, str]:
    """'top text | bottom text' -> ('top text', 'bottom text'). A single
    line with no '|' is treated as bottom text only, matching classic meme
    convention (caption goes at the bottom)."""
    raw = raw.strip()
    if not raw:
        return "", ""
    if "|" in raw:
        top, _, bottom = raw.partition("|")
        return top.strip(), bottom.strip()
    return "", raw


async def meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw_text = " ".join(context.args) if context.args else ""
    top, bottom = _parse_text(raw_text)

    if not top and not bottom:
        await update.message.reply_text(
            "Usage: `/meme top text | bottom text` (or just `/meme bottom text`).\n"
            "Tip: reply to a photo with /meme to use that image as the template.",
            parse_mode="Markdown",
        )
        return

    # If this command is a reply to a photo, use that as the template.
    reply = update.message.reply_to_message
    if reply and reply.photo:
        file = await reply.photo[-1].get_file()
        image_bytes = bytes(await file.download_as_bytearray())
    else:
        asset = library.random_asset(kind="image", category="memes") or library.random_asset(kind="image")
        if not asset:
            await update.message.reply_text(
                "No meme templates in the library yet. Drop images into "
                "assets/templates/memes/ on the server, or reply to a photo with /meme."
            )
            return
        with open(asset.abs_path, "rb") as f:
            image_bytes = f.read()

    try:
        result = meme_maker.make_meme(image_bytes, top_text=top, bottom_text=bottom)
    except meme_maker.MemeError as exc:
        await update.message.reply_text(f"Couldn't build that meme: {exc}")
        return

    await update.message.reply_photo(photo=result)
