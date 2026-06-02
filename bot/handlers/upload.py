import logging
from pyrogram import Client, enums, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot import database as db
from bot.utils.helpers import generate_unique_code, format_file_size, get_deep_link, check_rate_limit
from bot.config import STORAGE_CHANNEL_ID

logger = logging.getLogger(__name__)

SUPPORTED_TYPES = {
    "document": "📄",
    "video": "🎬",
    "audio": "🎵",
    "photo": "🖼️",
    "voice": "🎙️",
    "video_note": "📹",
    "animation": "🎞️",
    "sticker": "🎭",
}


def get_file_info(message: Message):
    if message.document:
        return message.document, "document"
    elif message.video:
        return message.video, "video"
    elif message.audio:
        return message.audio, "audio"
    elif message.photo:
        return message.photo, "photo"
    elif message.voice:
        return message.voice, "voice"
    elif message.video_note:
        return message.video_note, "video_note"
    elif message.animation:
        return message.animation, "animation"
    elif message.sticker:
        return message.sticker, "sticker"
    return None, None


def register_upload_handlers(app: Client):

    @app.on_message(
        filters.private &
        (
            filters.document | filters.video | filters.audio |
            filters.photo | filters.voice | filters.video_note |
            filters.animation | filters.sticker
        )
    )
    async def upload_handler(client: Client, message: Message):
        user = message.from_user

        if await db.is_banned(user.id):
            await message.reply_text("🚫 You have been banned from using this bot.")
            return

        if not check_rate_limit(user.id, max_calls=5, window=30):
            await message.reply_text("⚠️ Upload rate limit reached. Please wait a moment.")
            return

        # Check force join
        from bot.handlers.start import check_force_join
        joined, channels = await check_force_join(client, user.id)
        if not joined:
            from bot.keyboards.menus import force_join_keyboard
            access_denied_text = await db.get_bot_text("access_denied")
            await message.reply_text(
                access_denied_text,
                reply_markup=force_join_keyboard(channels),
                parse_mode=enums.ParseMode.HTML
            )
            return

        file_obj, file_type = get_file_info(message)
        if not file_obj:
            return

        # Get file metadata
        if file_type == "photo":
            file_id = file_obj[-1].file_id if isinstance(file_obj, list) else file_obj.file_id
            file_name = f"photo_{message.id}.jpg"
            file_size = file_obj[-1].file_size if isinstance(file_obj, list) else getattr(file_obj, "file_size", 0) or 0
        else:
            file_id = file_obj.file_id
            file_name = getattr(file_obj, "file_name", None) or f"{file_type}_{message.id}"
            file_size = getattr(file_obj, "file_size", 0) or 0

        # Check for duplicate file_id
        pool = await db.get_pool()
        existing = await pool.fetchrow("SELECT unique_code FROM files WHERE file_id = $1", file_id)
        if existing:
            from bot.config import BOT_USERNAME
            link = get_deep_link(BOT_USERNAME, existing["unique_code"])
            await message.reply_text(
                f"⚠️ <b>File already stored!</b>\n\n"
                f"🔗 <b>Existing Link:</b>\n<code>{link}</code>",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Copy Link", url=link)],
                    [InlineKeyboardButton("🏠 Home", callback_data="home")]
                ])
            )
            return

        status_msg = await message.reply_text("⏳ Storing your file...")

        try:
            # Copy message to storage channel (no "Forwarded from" tag, works reliably)
            copied = await message.copy(STORAGE_CHANNEL_ID)
            stored_file_id = None

            if copied.document:
                stored_file_id = copied.document.file_id
            elif copied.video:
                stored_file_id = copied.video.file_id
            elif copied.audio:
                stored_file_id = copied.audio.file_id
            elif copied.photo:
                photos = copied.photo
                stored_file_id = photos[-1].file_id if isinstance(photos, list) else photos.file_id
            elif copied.voice:
                stored_file_id = copied.voice.file_id
            elif copied.video_note:
                stored_file_id = copied.video_note.file_id
            elif copied.animation:
                stored_file_id = copied.animation.file_id
            elif copied.sticker:
                stored_file_id = copied.sticker.file_id
            else:
                stored_file_id = file_id

            # Generate unique code
            unique_code = generate_unique_code()
            while await db.get_file_by_code(unique_code):
                unique_code = generate_unique_code()

            # Save metadata
            await db.save_file(unique_code, file_name, stored_file_id, file_size, user.id, file_type)

            from bot.config import BOT_USERNAME
            link = get_deep_link(BOT_USERNAME, unique_code)
            emoji = SUPPORTED_TYPES.get(file_type, "📁")

            await status_msg.edit_text(
                f"✅ <b>File Stored Successfully</b>\n\n"
                f"{emoji} <b>File Name:</b> <code>{file_name}</code>\n"
                f"📦 <b>File Size:</b> {format_file_size(file_size)}\n\n"
                f"🔗 <b>Permanent Link:</b>\n<code>{link}</code>\n\n"
                f"Share this link with anyone.",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Share Link", url=f"https://t.me/share/url?url={link}")],
                    [InlineKeyboardButton("🏠 Home", callback_data="home")]
                ])
            )
            logger.info(f"User {user.id} uploaded file: {file_name} ({unique_code})")

        except Exception as e:
            logger.error(f"Upload error for user {user.id}: {e}")
            await status_msg.edit_text(
                "❌ <b>Upload failed.</b> Please try again.",
                parse_mode=enums.ParseMode.HTML
            )
