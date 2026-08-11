from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from services import image_gen, ratelimit


async def art_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = " ".join(context.args) if context.args else ""
    if not prompt:
        await update.message.reply_text(
            "Usage: `/art a description of the scene you want the $IF guy in`\n"
            "Example: `/art riding a rocket through a green nebula`",
            parse_mode="Markdown",
        )
        return

    wait = ratelimit.check(update.effective_user.id, "art")
    if wait:
        await update.message.reply_text(f"Slow down a bit — try again in {wait}s.")
        return

    full_prompt = image_gen.build_character_prompt(prompt)
    await _generate_and_send(update, full_prompt)


async def variations_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        key = context.args[0].lower()
        scene = image_gen.PRESET_SCENES.get(key)
        if not scene:
            options = ", ".join(image_gen.PRESET_SCENES.keys())
            await update.message.reply_text(f"Unknown scene. Options: {options}")
            return

        wait = ratelimit.check(update.effective_user.id, "art")
        if wait:
            await update.message.reply_text(f"Slow down a bit — try again in {wait}s.")
            return

        await _generate_and_send(update, image_gen.build_character_prompt(scene))
        return

    buttons = [
        InlineKeyboardButton(key.replace("_", " ").title(), callback_data=f"variation:{key}")
        for key in image_gen.PRESET_SCENES
    ]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    await update.message.reply_text(
        "Pick a scene for the $IF guy:", reply_markup=InlineKeyboardMarkup(rows)
    )


async def variation_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    key = query.data.split(":", 1)[1]
    scene = image_gen.PRESET_SCENES.get(key)
    if not scene:
        await query.message.reply_text("That scene isn't available anymore.")
        return

    wait = ratelimit.check(update.effective_user.id, "art")
    if wait:
        await query.message.reply_text(f"Slow down a bit — try again in {wait}s.")
        return

    await _generate_and_send(update, image_gen.build_character_prompt(scene), via_query=query)


async def _generate_and_send(update: Update, prompt: str, via_query=None) -> None:
    chat = update.effective_chat
    status = await chat.send_message("Generating...")
    try:
        image_bytes = await image_gen.generate_image(prompt)
    except image_gen.ImageGenError as exc:
        await status.edit_text(f"Generation failed: {exc}")
        return
    except Exception:
        await status.edit_text("Generation failed unexpectedly. Try again in a moment.")
        return

    await status.delete()
    await chat.send_photo(photo=image_bytes)
