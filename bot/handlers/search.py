import logging
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, ForceReply

from bot import database as db
from bot.keyboards.menus import search_results_keyboard, back_to_home
from bot.utils.helpers import check_rate_limit, format_file_size

logger = logging.getLogger(__name__)

_pending_search: dict = {}


def register_search_handlers(app: Client):

    @app.on_callback_query(filters.regex("^search_files$"))
    async def search_prompt(client: Client, query: CallbackQuery):
        _pending_search[query.from_user.id] = True
        await query.message.edit_text(
            "🔍 <b>Search Files</b>\n\nSend me the filename or keyword to search for:",
            reply_markup=back_to_home(),
            parse_mode="html"
        )

    @app.on_message(filters.private & filters.text & ~filters.command(["start", "help", "admin", "stats", "broadcast", "ban", "unban", "addadmin", "removeadmin", "addchannel", "removechannel", "deletefile"]))
    async def search_text_handler(client: Client, message: Message):
        user_id = message.from_user.id

        if user_id not in _pending_search:
            return

        if await db.is_banned(user_id):
            return

        if not check_rate_limit(user_id, max_calls=5, window=10):
            await message.reply_text("⚠️ Too many requests. Please slow down.")
            return

        _pending_search.pop(user_id, None)
        query_text = message.text.strip()

        if len(query_text) < 2:
            await message.reply_text("⚠️ Search query too short. Please enter at least 2 characters.")
            return

        await perform_search(client, message, query_text, 0)

    @app.on_callback_query(filters.regex(r"^search_page_(.+)_(\d+)$"))
    async def search_page_callback(client: Client, query: CallbackQuery):
        parts = query.data.split("_")
        offset = int(parts[-1])
        search_query = "_".join(parts[2:-1])
        await perform_search(client, query, search_query, offset, edit=True)


async def perform_search(client, message_or_query, query_text: str, offset: int, edit: bool = False):
    per_page = 10
    results = await db.search_files(query_text, offset, per_page)
    total = await db.search_files_count(query_text)

    if not results:
        text = f"🔍 No files found for: <b>{query_text}</b>"
        if isinstance(message_or_query, CallbackQuery) and edit:
            await message_or_query.message.edit_text(text, reply_markup=back_to_home(), parse_mode="html")
        else:
            target = message_or_query.message if isinstance(message_or_query, CallbackQuery) else message_or_query
            await target.reply_text(text, reply_markup=back_to_home(), parse_mode="html")
        return

    text = (
        f"🔍 <b>Search Results</b>\n\n"
        f"Query: <b>{query_text}</b>\n"
        f"Found: <b>{total}</b> file(s)\n\n"
        f"Tap a file to download it:"
    )
    kb = search_results_keyboard(results, query_text, offset, total, per_page)

    if isinstance(message_or_query, CallbackQuery) and edit:
        await message_or_query.message.edit_text(text, reply_markup=kb, parse_mode="html")
    else:
        target = message_or_query.message if isinstance(message_or_query, CallbackQuery) else message_or_query
        await target.reply_text(text, reply_markup=kb, parse_mode="html")
