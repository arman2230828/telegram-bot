import logging
from pyrogram import Client, filters
from pyrogram.types import Message

from bot import database as db

logger = logging.getLogger(__name__)


def register_stats_handlers(app: Client):

    @app.on_message(filters.command("users") & filters.private)
    async def users_command(client: Client, message: Message):
        if not await db.is_admin(message.from_user.id):
            return
        pool = await db.get_pool()
        total = await pool.fetchval("SELECT COUNT(*) FROM users")
        banned = await pool.fetchval("SELECT COUNT(*) FROM users WHERE is_banned = TRUE")
        premium = await pool.fetchval("SELECT COUNT(*) FROM users WHERE is_premium = TRUE")
        await message.reply_text(
            f"👥 <b>User Statistics</b>\n\n"
            f"Total: <b>{total}</b>\n"
            f"Banned: <b>{banned}</b>\n"
            f"Premium: <b>{premium}</b>",
            parse_mode="html"
        )

    @app.on_message(filters.command("files") & filters.private)
    async def files_command(client: Client, message: Message):
        if not await db.is_admin(message.from_user.id):
            return
        pool = await db.get_pool()
        total = await pool.fetchval("SELECT COUNT(*) FROM files")
        total_size = await pool.fetchval("SELECT COALESCE(SUM(file_size), 0) FROM files")
        from bot.utils.helpers import format_file_size
        await message.reply_text(
            f"📁 <b>File Statistics</b>\n\n"
            f"Total Files: <b>{total}</b>\n"
            f"Total Size: <b>{format_file_size(total_size)}</b>",
            parse_mode="html"
        )
