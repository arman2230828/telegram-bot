import logging
from pyrogram import Client, enums, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot import database as db
from bot.utils.helpers import format_file_size, check_rate_limit

logger = logging.getLogger(__name__)


async def send_file_by_type(client: Client, user_id: int, file_record: dict):
    """Send file using the correct Pyrogram method based on stored file_type.
    Falls back through all media types automatically if the stored type is wrong."""
    file_id = file_record["file_id"]
    file_name = file_record["file_name"]
    file_size = file_record["file_size"]
    file_type = file_record.get("file_type") or "document"
    unique_code = file_record.get("unique_code")
    download_count = file_record["download_count"] + 1

    caption = (
        f"📄 <b>{file_name}</b>\n"
        f"📦 Size: {format_file_size(file_size)}\n"
        f"⬇️ Downloads: {download_count}"
    )

    # Map of type → send coroutine factory
    senders = {
        "photo":      lambda: client.send_photo(user_id, photo=file_id, caption=caption, parse_mode=enums.ParseMode.HTML),
        "video":      lambda: client.send_video(user_id, video=file_id, caption=caption, parse_mode=enums.ParseMode.HTML),
        "audio":      lambda: client.send_audio(user_id, audio=file_id, caption=caption, parse_mode=enums.ParseMode.HTML),
        "voice":      lambda: client.send_voice(user_id, voice=file_id),
        "video_note": lambda: client.send_video_note(user_id, video_note=file_id),
        "animation":  lambda: client.send_animation(user_id, animation=file_id, caption=caption, parse_mode=enums.ParseMode.HTML),
        "sticker":    lambda: client.send_sticker(user_id, sticker=file_id),
        "document":   lambda: client.send_document(user_id, document=file_id, caption=caption, parse_mode=enums.ParseMode.HTML),
    }

    # Try stored type first, then fall back through all others
    order = [file_type] + [t for t in senders if t != file_type]
    last_err = None
    for t in order:
        try:
            await senders[t]()
            # If the type we used differs from stored, auto-correct it in DB
            if t != file_type and unique_code:
                pool = await db.get_pool()
                await pool.execute("UPDATE files SET file_type = $1 WHERE unique_code = $2", t, unique_code)
                logger.info(f"Auto-corrected file_type {file_type!r} → {t!r} for {unique_code}")
            return
        except Exception as e:
            last_err = e
            if "Expected" in str(e) and "got" in str(e):
                continue   # wrong type — try next
            raise          # real error — bubble up
    raise last_err


async def handle_file_download(client: Client, message_or_query, unique_code: str):
    if isinstance(message_or_query, CallbackQuery):
        user = message_or_query.from_user
        reply_func = message_or_query.message.reply_text
        answer_func = message_or_query.answer
    else:
        user = message_or_query.from_user
        reply_func = message_or_query.reply_text
        answer_func = None

    if await db.is_banned(user.id):
        await reply_func("🚫 You have been banned.")
        return

    if not check_rate_limit(user.id, max_calls=10, window=60):
        if answer_func:
            await answer_func("⚠️ Too many requests. Please slow down.", show_alert=True)
        else:
            await reply_func("⚠️ Too many requests. Please slow down.")
        return

    file_record = await db.get_file_by_code(unique_code)
    if not file_record:
        await reply_func(
            "❌ <b>File not found.</b> The link may be invalid or the file was deleted.",
            parse_mode=enums.ParseMode.HTML
        )
        return

    try:
        status = await reply_func("⏳ Fetching your file...")
        await db.increment_download_count(unique_code, user.id)
        await send_file_by_type(client, user.id, file_record)
        await status.delete()
        logger.info(f"User {user.id} downloaded file: {file_record['file_name']} ({unique_code})")

    except Exception as e:
        logger.error(f"Download error for {unique_code}: {e}")
        try:
            await status.edit_text(
                "❌ <b>Download failed.</b> Please try again.",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass


def register_download_handlers(app: Client):

    @app.on_callback_query(filters.regex(r"^dl_(.+)$"))
    async def download_callback(client: Client, query: CallbackQuery):
        unique_code = query.data[3:]

        from bot.handlers.start import check_force_join
        joined, channels = await check_force_join(client, query.from_user.id)
        if not joined:
            from bot.keyboards.menus import force_join_keyboard
            access_denied = await db.get_bot_text("access_denied")
            await query.message.edit_text(
                access_denied,
                reply_markup=force_join_keyboard(channels),
                parse_mode=enums.ParseMode.HTML
            )
            return

        await handle_file_download(client, query, unique_code)

    @app.on_callback_query(filters.regex(r"^file_info_(.+)$"))
    async def file_info_callback(client: Client, query: CallbackQuery):
        unique_code = query.data[10:]
        file_record = await db.get_file_by_code(unique_code)
        if not file_record:
            await query.answer("❌ File not found.", show_alert=True)
            return

        from bot.keyboards.menus import file_info_keyboard
        from bot.config import BOT_USERNAME
        from bot.utils.helpers import get_deep_link
        is_owner = file_record["uploader_id"] == query.from_user.id
        link = get_deep_link(BOT_USERNAME, unique_code)

        await query.message.edit_text(
            f"📄 <b>File Info</b>\n\n"
            f"<b>Name:</b> <code>{file_record['file_name']}</code>\n"
            f"<b>Size:</b> {format_file_size(file_record['file_size'])}\n"
            f"<b>Downloads:</b> {file_record['download_count']}\n"
            f"<b>Uploaded:</b> {file_record['upload_date'].strftime('%Y-%m-%d %H:%M')}\n\n"
            f"🔗 <b>Link:</b>\n<code>{link}</code>",
            reply_markup=file_info_keyboard(unique_code, is_owner),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex(r"^del_(.+)$"))
    async def delete_file_callback(client: Client, query: CallbackQuery):
        unique_code = query.data[4:]
        file_record = await db.get_file_by_code(unique_code)
        if not file_record:
            await query.answer("❌ File not found.", show_alert=True)
            return

        if file_record["uploader_id"] != query.from_user.id:
            if not await db.is_admin(query.from_user.id):
                await query.answer("❌ You can only delete your own files.", show_alert=True)
                return

        await db.delete_file(unique_code)
        await query.message.edit_text(
            "✅ <b>File deleted successfully.</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="home")]]),
            parse_mode=enums.ParseMode.HTML
        )
