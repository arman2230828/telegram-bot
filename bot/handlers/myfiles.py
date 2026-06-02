import logging
from pyrogram import Client, enums, filters
from pyrogram.types import CallbackQuery

from bot import database as db
from bot.keyboards.menus import my_files_keyboard, back_to_home
from bot.utils.helpers import format_file_size

logger = logging.getLogger(__name__)

PER_PAGE = 10


def register_myfiles_handlers(app: Client):

    @app.on_callback_query(filters.regex(r"^my_files_(\d+)$"))
    async def my_files_callback(client: Client, query: CallbackQuery):
        user_id = query.from_user.id
        offset = int(query.data.split("_")[-1])

        pool = await db.get_pool()
        total = await pool.fetchval("SELECT COUNT(*) FROM files WHERE uploader_id = $1", user_id)
        files = await db.get_user_files(user_id, offset, PER_PAGE)

        user = await db.get_user(user_id)
        total_uploads = user["total_uploads"] if user else 0

        if not files:
            await query.message.edit_text(
                "📁 <b>My Files</b>\n\nYou haven't uploaded any files yet.\n\nSend a file to get started!",
                reply_markup=back_to_home(),
                parse_mode=enums.ParseMode.HTML
            )
            return

        text = (
            f"📁 <b>My Files</b>\n\n"
            f"Total Uploads: <b>{total_uploads}</b>\n"
            f"Showing {offset + 1}–{min(offset + PER_PAGE, total)} of {total}\n\n"
            f"Tap a file for more options:"
        )
        await query.message.edit_text(
            text,
            reply_markup=my_files_keyboard(files, offset, total, PER_PAGE),
            parse_mode=enums.ParseMode.HTML
        )
