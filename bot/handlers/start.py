import logging
from pyrogram import Client, enums, filters
from pyrogram.types import Message, CallbackQuery

from bot import database as db
from bot.keyboards.menus import home_menu, force_join_keyboard, back_to_home
from bot.utils.helpers import check_rate_limit, get_referral_link
from bot.handlers.download import handle_file_download

logger = logging.getLogger(__name__)


async def check_force_join(client: Client, user_id: int) -> tuple[bool, list]:
    channels = await db.get_force_join_channels()
    if not channels:
        return True, []
    not_joined = []
    for ch in channels:
        try:
            member = await client.get_chat_member(int(ch["channel_id"]), user_id)
            from pyrogram.enums import ChatMemberStatus
            if member.status in (ChatMemberStatus.BANNED, ChatMemberStatus.LEFT):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return len(not_joined) == 0, list(channels)


async def show_home_menu(client: Client, message_or_query, welcome_text: str = None):
    if welcome_text is None:
        welcome_text = await db.get_bot_text("welcome_message")
    if isinstance(message_or_query, CallbackQuery):
        try:
            await message_or_query.message.edit_text(
                welcome_text,
                reply_markup=home_menu(),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            await message_or_query.message.reply_text(
                welcome_text,
                reply_markup=home_menu(),
                parse_mode=enums.ParseMode.HTML
            )
    else:
        await message_or_query.reply_text(
            welcome_text,
            reply_markup=home_menu(),
            parse_mode=enums.ParseMode.HTML
        )


def register_start_handlers(app: Client):

    @app.on_message(filters.command("start") & filters.private)
    async def start_handler(client: Client, message: Message):
        user = message.from_user
        await db.upsert_user(user.id, user.username, user.first_name)

        if await db.is_banned(user.id):
            await message.reply_text("🚫 You have been banned from using this bot.")
            return

        if not check_rate_limit(user.id):
            await message.reply_text("⚠️ You are sending requests too fast. Please slow down.")
            return

        args = message.command[1] if len(message.command) > 1 else ""

        # Handle referral
        if args.startswith("ref_"):
            try:
                referrer_id = int(args[4:])
                if referrer_id != user.id:
                    added = await db.add_referral(referrer_id, user.id)
                    if added:
                        try:
                            from bot.config import BOT_USERNAME
                            ref_link = get_referral_link(BOT_USERNAME, referrer_id)
                            await client.send_message(
                                referrer_id,
                                f"🎉 <b>New Referral!</b>\n\n"
                                f"<b>{user.first_name}</b> joined using your referral link!\n"
                                f"Your referral count has increased.",
                                parse_mode=enums.ParseMode.HTML
                            )
                        except Exception:
                            pass
            except (ValueError, IndexError):
                pass

        # Handle file download via deep link
        if args.startswith("file_"):
            code = args[5:]
            joined, channels = await check_force_join(client, user.id)
            if not joined:
                access_denied_text = await db.get_bot_text("access_denied")
                sent = await message.reply_text(
                    access_denied_text,
                    reply_markup=force_join_keyboard(channels),
                    parse_mode=enums.ParseMode.HTML
                )
                # Store the file code to redirect after join
                return

            await handle_file_download(client, message, code)
            return

        # Check force join
        joined, channels = await check_force_join(client, user.id)
        if not joined:
            access_denied_text = await db.get_bot_text("access_denied")
            await message.reply_text(
                access_denied_text,
                reply_markup=force_join_keyboard(channels),
                parse_mode=enums.ParseMode.HTML
            )
            return

        await show_home_menu(client, message)

    @app.on_callback_query(filters.regex("^verify_join$"))
    async def verify_join_handler(client: Client, query: CallbackQuery):
        user = query.from_user
        joined, channels = await check_force_join(client, user.id)

        if joined:
            verify_success = await db.get_bot_text("verify_success")
            try:
                await query.message.edit_text(verify_success, parse_mode=enums.ParseMode.HTML)
            except Exception:
                pass
            welcome_text = await db.get_bot_text("welcome_message")
            await query.message.reply_text(
                welcome_text,
                reply_markup=home_menu(),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            verify_failed = await db.get_bot_text("verify_failed")
            access_denied_text = await db.get_bot_text("access_denied")
            await query.answer(verify_failed, show_alert=True)
            try:
                await query.message.edit_text(
                    access_denied_text,
                    reply_markup=force_join_keyboard(channels),
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                pass

    @app.on_callback_query(filters.regex("^home$"))
    async def home_callback(client: Client, query: CallbackQuery):
        if await db.is_banned(query.from_user.id):
            await query.answer("🚫 You are banned.", show_alert=True)
            return
        joined, channels = await check_force_join(client, query.from_user.id)
        if not joined:
            access_denied_text = await db.get_bot_text("access_denied")
            try:
                await query.message.edit_text(
                    access_denied_text,
                    reply_markup=force_join_keyboard(channels),
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                pass
            return
        await show_home_menu(client, query)

    @app.on_callback_query(filters.regex("^upload_file$"))
    async def upload_prompt(client: Client, query: CallbackQuery):
        await query.message.edit_text(
            "📤 <b>Upload a File</b>\n\nSend me any file, photo, video, audio, or document to store it.\n\n"
            "Supported: APK, ZIP, PDF, Video, Audio, Images, Documents",
            reply_markup=back_to_home(),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^support$"))
    async def support_callback(client: Client, query: CallbackQuery):
        await query.message.edit_text(
            "🆘 <b>Support</b>\n\nFor help and support, please contact the admin.\n\n"
            "You can also use /help for a list of commands.",
            reply_markup=back_to_home(),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^premium$"))
    async def premium_callback(client: Client, query: CallbackQuery):
        await query.message.edit_text(
            "⭐ <b>Premium</b>\n\nPremium features coming soon!\n\n"
            "Stay tuned for updates.",
            reply_markup=back_to_home(),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^help$"))
    async def help_callback(client: Client, query: CallbackQuery):
        await query.message.edit_text(
            "❓ <b>Help</b>\n\n"
            "<b>How to use:</b>\n"
            "1. Send any file to upload it\n"
            "2. Get a permanent shareable link\n"
            "3. Share the link with anyone\n"
            "4. Recipients open the link to download instantly\n\n"
            "<b>Commands:</b>\n"
            "/start — Start the bot\n"
            "/help — Show this message\n\n"
            "<b>Deep Link Format:</b>\n"
            "<code>https://t.me/BOT?start=file_CODE</code>",
            reply_markup=back_to_home(),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_message(filters.command("help") & filters.private)
    async def help_command(client: Client, message: Message):
        await message.reply_text(
            "❓ <b>Help</b>\n\n"
            "<b>How to use:</b>\n"
            "1. Send any file to upload it\n"
            "2. Get a permanent shareable link\n"
            "3. Share the link with anyone\n\n"
            "<b>Commands:</b>\n"
            "/start — Start the bot\n"
            "/help — Show this message",
            parse_mode=enums.ParseMode.HTML
        )
