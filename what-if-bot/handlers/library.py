from telegram import Update
from telegram.ext import ContextTypes

from services import library as art_library

_ANIMATION_VIDEO_EXTS = {".webm", ".mov"}


async def _send_asset(update: Update, asset: art_library.Asset) -> None:
    with open(asset.abs_path, "rb") as f:
        data = f.read()

    ext = asset.rel_path.rsplit(".", 1)[-1].lower()
    if asset.kind == "image":
        await update.message.reply_photo(photo=data)
    elif ext in ("gif", "mp4"):
        await update.message.reply_animation(animation=data)
    else:
        await update.message.reply_video(video=data)


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    asset = art_library.random_asset()
    if not asset:
        await update.message.reply_text(
            "The art library is empty. Drop images/GIFs into assets/templates/ on "
            "the server (any subfolder), then run scripts/build_manifest.py."
        )
        return
    await _send_asset(update, asset)


async def gif_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    asset = art_library.random_asset(kind="animation")
    if not asset:
        await update.message.reply_text(
            "No animations in the library yet. Drop .gif/.mp4 files into "
            "assets/templates/ on the server."
        )
        return
    await _send_asset(update, asset)
