import logging
import asyncio
from pyrogram import Client, enums, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot import database as db
from bot.keyboards.menus import (
    admin_panel_keyboard, broadcast_target_keyboard,
    broadcast_schedule_keyboard, edit_texts_keyboard, back_to_home
)

logger = logging.getLogger(__name__)

_pending_admin_action: dict = {}
_pending_broadcast: dict = {}


def register_admin_handlers(app: Client):

    # /admin command removed — use Web Admin Panel instead

    @app.on_callback_query(filters.regex("^admin_panel$"))
    async def admin_panel_callback(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        await query.message.edit_text(
            "🔧 <b>Admin Panel</b>\n\nChoose an action:",
            reply_markup=admin_panel_keyboard(),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^admin_stats$"))
    async def admin_stats_callback(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        stats = await db.get_stats()
        await query.message.edit_text(
            f"📊 <b>Bot Statistics</b>\n\n"
            f"👥 Total Users: <b>{stats['total_users']}</b>\n"
            f"📁 Total Files: <b>{stats['total_files']}</b>\n"
            f"⬇️ Total Downloads: <b>{stats['total_downloads']}</b>\n"
            f"⭐ Premium Users: <b>{stats['premium_users']}</b>\n\n"
            f"📅 <b>Today</b>\n"
            f"📤 Daily Uploads: <b>{stats['daily_uploads']}</b>\n"
            f"👤 Daily Joins: <b>{stats['daily_joins']}</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="admin_panel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^admin_ban$"))
    async def admin_ban_prompt(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        _pending_admin_action[query.from_user.id] = "ban"
        await query.message.edit_text(
            "🚫 <b>Ban User</b>\n\nReply with the user ID to ban:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✕ Cancel", callback_data="admin_panel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^admin_unban$"))
    async def admin_unban_prompt(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        _pending_admin_action[query.from_user.id] = "unban"
        await query.message.edit_text(
            "✅ <b>Unban User</b>\n\nReply with the user ID to unban:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✕ Cancel", callback_data="admin_panel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^admin_addadmin$"))
    async def admin_addadmin_prompt(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        _pending_admin_action[query.from_user.id] = "addadmin"
        await query.message.edit_text(
            "👑 <b>Add Admin</b>\n\nReply with the user ID to promote:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✕ Cancel", callback_data="admin_panel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^admin_removeadmin$"))
    async def admin_removeadmin_prompt(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        _pending_admin_action[query.from_user.id] = "removeadmin"
        await query.message.edit_text(
            "➖ <b>Remove Admin</b>\n\nReply with the user ID to demote:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✕ Cancel", callback_data="admin_panel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^admin_addchannel$"))
    async def admin_addchannel_prompt(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        _pending_admin_action[query.from_user.id] = "addchannel"
        await query.message.edit_text(
            "📡 <b>Add Force Join Channel</b>\n\n"
            "Reply with the channel ID (e.g. <code>-1001234567890</code>) or username (e.g. <code>@mychannel</code>):\n\n"
            "⚠️ Make sure the bot is an admin in the channel.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✕ Cancel", callback_data="admin_panel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^admin_removechannel$"))
    async def admin_removechannel_prompt(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        channels = await db.get_force_join_channels()
        if not channels:
            await query.answer("No channels configured.", show_alert=True)
            return
        _pending_admin_action[query.from_user.id] = "removechannel"
        ch_list = "\n".join([f"• <code>{ch['channel_id']}</code> ({ch['channel_username'] or 'private'})" for ch in channels])
        await query.message.edit_text(
            f"🗑 <b>Remove Force Join Channel</b>\n\nCurrent channels:\n{ch_list}\n\nReply with the channel ID to remove:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✕ Cancel", callback_data="admin_panel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^admin_deletefile$"))
    async def admin_deletefile_prompt(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        _pending_admin_action[query.from_user.id] = "deletefile"
        await query.message.edit_text(
            "🗑 <b>Delete File</b>\n\nReply with the unique file code to delete:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✕ Cancel", callback_data="admin_panel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^admin_edittexts$"))
    async def admin_edittexts_callback(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        await query.message.edit_text(
            "📝 <b>Edit Bot Texts</b>\n\nChoose which text to edit:",
            reply_markup=edit_texts_keyboard(),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex(r"^edittext_(.+)$"))
    async def edittext_prompt(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        key = query.data[9:]
        current = await db.get_bot_text(key)
        _pending_admin_action[query.from_user.id] = f"edittext_{key}"
        await query.message.edit_text(
            f"📝 <b>Edit: {key}</b>\n\n"
            f"<b>Current value:</b>\n<code>{current}</code>\n\n"
            f"Reply with the new text (HTML formatting supported):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✕ Cancel", callback_data="admin_edittexts")]]),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^admin_broadcast$"))
    async def admin_broadcast_callback(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        await query.message.edit_text(
            "📢 <b>Broadcast</b>\n\nChoose your target audience:",
            reply_markup=broadcast_target_keyboard(),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex(r"^bcast_target_(.+)$"))
    async def bcast_target_callback(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        target = query.data[13:]
        await query.message.edit_text(
            f"📢 <b>Broadcast — Schedule</b>\n\nTarget: <b>{target}</b>\n\nWhen to send?",
            reply_markup=broadcast_schedule_keyboard(target),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex(r"^bcast_schedule_(.+)_(.+)$"))
    async def bcast_schedule_callback(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        parts = query.data.split("_")
        schedule = parts[2]
        target = "_".join(parts[3:])
        _pending_broadcast[query.from_user.id] = {"target": target, "schedule": schedule}
        await query.message.edit_text(
            f"📢 <b>Broadcast</b>\n\nTarget: <b>{target}</b> | Schedule: <b>{schedule}</b>\n\n"
            f"Now send the message you want to broadcast.\n\n"
            f"Supports: Text, Photos, Videos, Documents, Stickers, Voice, Forwarded messages.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✕ Cancel", callback_data="admin_panel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^admin_bcast_history$"))
    async def bcast_history_callback(client: Client, query: CallbackQuery):
        if not await db.is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized.", show_alert=True)
            return
        history = await db.get_broadcast_history()
        if not history:
            await query.answer("No broadcast history.", show_alert=True)
            return
        lines = []
        for h in history:
            lines.append(
                f"📅 {h['sent_at'].strftime('%Y-%m-%d %H:%M')} | Target: {h['target_group']}\n"
                f"✅ {h['total_delivered']} delivered | ❌ {h['total_failed']} failed"
            )
        await query.message.edit_text(
            "📜 <b>Broadcast History</b>\n\n" + "\n\n".join(lines),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="admin_panel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    # ─── TEXT MESSAGE HANDLER for pending admin actions ──────────────────────

    @app.on_message(filters.private & filters.text & ~filters.command([
        "start", "help", "stats"
    ]))
    async def admin_text_handler(client: Client, message: Message):
        user_id = message.from_user.id

        if user_id in _pending_admin_action:
            action = _pending_admin_action.pop(user_id)
            await handle_admin_text_action(client, message, action)
            message.stop_propagation()
            return

        if user_id in _pending_broadcast:
            bcast_info = _pending_broadcast.pop(user_id)
            await handle_broadcast_message(client, message, bcast_info)
            message.stop_propagation()
            return

    # ─── MEDIA BROADCAST HANDLER (must be before upload handler) ─────────────

    @app.on_message(filters.private & (
        filters.photo | filters.video | filters.document |
        filters.audio | filters.voice | filters.sticker | filters.animation
    ))
    async def admin_media_broadcast_handler(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id in _pending_broadcast:
            bcast_info = _pending_broadcast.pop(user_id)
            await handle_broadcast_message(client, message, bcast_info)
            message.stop_propagation()  # prevent upload handler from firing


async def handle_admin_text_action(client: Client, message: Message, action: str):
    text = message.text.strip()

    if action == "ban":
        try:
            target_id = int(text)
            await db.ban_user(target_id)
            await message.reply_text(f"✅ User <code>{target_id}</code> has been banned.", parse_mode=enums.ParseMode.HTML)
        except ValueError:
            await message.reply_text("❌ Invalid user ID.")

    elif action == "unban":
        try:
            target_id = int(text)
            await db.unban_user(target_id)
            await message.reply_text(f"✅ User <code>{target_id}</code> has been unbanned.", parse_mode=enums.ParseMode.HTML)
        except ValueError:
            await message.reply_text("❌ Invalid user ID.")

    elif action == "addadmin":
        try:
            target_id = int(text)
            await db.add_admin(target_id)
            await message.reply_text(f"✅ User <code>{target_id}</code> is now an admin.", parse_mode=enums.ParseMode.HTML)
        except ValueError:
            await message.reply_text("❌ Invalid user ID.")

    elif action == "removeadmin":
        try:
            target_id = int(text)
            await db.remove_admin(target_id)
            await message.reply_text(f"✅ User <code>{target_id}</code> removed from admins.", parse_mode=enums.ParseMode.HTML)
        except ValueError:
            await message.reply_text("❌ Invalid user ID.")

    elif action == "addchannel":
        try:
            ch_id = text
            ch_username = text if text.startswith("@") else None
            await db.add_force_join_channel(ch_id, ch_username)
            await message.reply_text(f"✅ Channel <code>{ch_id}</code> added to force join.", parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            await message.reply_text(f"❌ Error: {e}")

    elif action == "removechannel":
        await db.remove_force_join_channel(text)
        await message.reply_text(f"✅ Channel <code>{text}</code> removed.", parse_mode=enums.ParseMode.HTML)

    elif action == "deletefile":
        file_record = await db.get_file_by_code(text)
        if not file_record:
            await message.reply_text("❌ File not found.")
        else:
            await db.delete_file(text)
            await message.reply_text(f"✅ File <code>{text}</code> deleted.", parse_mode=enums.ParseMode.HTML)

    elif action.startswith("edittext_"):
        key = action[9:]
        await db.set_bot_text(key, text)
        await message.reply_text(
            f"✅ Text <b>{key}</b> updated successfully.",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Edit Texts", callback_data="admin_edittexts")]])
        )


async def handle_broadcast_message(client: Client, message: Message, bcast_info: dict):
    target = bcast_info["target"]
    schedule = bcast_info["schedule"]

    delay = 0
    if schedule == "1h":
        delay = 3600
    elif schedule == "24h":
        delay = 86400

    await message.reply_text(
        f"📢 <b>Broadcast Queued</b>\n\n"
        f"Target: <b>{target}</b>\n"
        f"Schedule: <b>{schedule}</b>\n\n"
        f"{'Starting immediately...' if delay == 0 else f'Will start in {schedule}.'}",
        parse_mode=enums.ParseMode.HTML
    )

    asyncio.create_task(_run_broadcast(client, message, target, delay))


async def _run_broadcast(client: Client, message: Message, target: str, delay: int):
    if delay > 0:
        await asyncio.sleep(delay)

    user_ids = await db.get_all_user_ids(target)
    delivered = 0
    failed = 0
    blocked = 0

    for uid in user_ids:
        try:
            await asyncio.sleep(0.05)
            if message.text:
                await client.send_message(uid, message.text, parse_mode=enums.ParseMode.HTML)
            elif message.photo:
                photos = message.photo
                file_id = photos[-1].file_id if isinstance(photos, list) else photos.file_id
                await client.send_photo(uid, file_id, caption=message.caption or "", parse_mode=enums.ParseMode.HTML)
            elif message.video:
                await client.send_video(uid, message.video.file_id, caption=message.caption or "", parse_mode=enums.ParseMode.HTML)
            elif message.document:
                await client.send_document(uid, message.document.file_id, caption=message.caption or "", parse_mode=enums.ParseMode.HTML)
            elif message.audio:
                await client.send_audio(uid, message.audio.file_id, caption=message.caption or "", parse_mode=enums.ParseMode.HTML)
            elif message.voice:
                await client.send_voice(uid, message.voice.file_id)
            elif message.sticker:
                await client.send_sticker(uid, message.sticker.file_id)
            elif message.animation:
                await client.send_animation(uid, message.animation.file_id, caption=message.caption or "", parse_mode=enums.ParseMode.HTML)
            delivered += 1
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err:
                blocked += 1
            failed += 1

    summary = (
        f"✅ <b>Broadcast Completed</b>\n\n"
        f"👥 Total: <b>{len(user_ids)}</b>\n"
        f"✅ Delivered: <b>{delivered}</b>\n"
        f"❌ Failed: <b>{failed}</b>\n"
        f"🚫 Blocked: <b>{blocked}</b>"
    )
    try:
        await message.reply_text(summary, parse_mode=enums.ParseMode.HTML)
    except Exception:
        pass

    await db.save_broadcast(
        message_content=message.text or f"[media: {message.media}]",
        delivered=delivered,
        failed=failed,
        target=target
    )
