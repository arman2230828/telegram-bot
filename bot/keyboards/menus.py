from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def home_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📤 Upload File", callback_data="upload_file"),
            InlineKeyboardButton("📁 My Files", callback_data="my_files_0"),
        ],
        [
            InlineKeyboardButton("🔍 Search Files", callback_data="search_files"),
            InlineKeyboardButton("👥 Referral", callback_data="referral"),
        ],
        [
            InlineKeyboardButton("⭐ Premium", callback_data="premium"),
            InlineKeyboardButton("🆘 Support", callback_data="support"),
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help"),
        ],
    ])


def back_to_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Home", callback_data="home")]
    ])


def force_join_keyboard(channels: list, bot_username: str = None) -> InlineKeyboardMarkup:
    buttons = []
    for i, ch in enumerate(channels, 1):
        username = ch["channel_username"]
        if username:
            url = f"https://t.me/{username.lstrip('@')}"
        else:
            url = f"https://t.me/c/{str(ch['channel_id']).lstrip('-100')}"
        buttons.append([InlineKeyboardButton(f"📢 Join Channel {i}", url=url)])
    buttons.append([InlineKeyboardButton("✅ I Joined", callback_data="verify_join")])
    return InlineKeyboardMarkup(buttons)


def my_files_keyboard(files: list, offset: int, total: int, per_page: int = 10) -> InlineKeyboardMarkup:
    buttons = []
    for f in files:
        buttons.append([
            InlineKeyboardButton(
                f"📄 {f['file_name'][:35]}",
                callback_data=f"file_info_{f['unique_code']}"
            )
        ])
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"my_files_{offset - per_page}"))
    if offset + per_page < total:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"my_files_{offset + per_page}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("🏠 Home", callback_data="home")])
    return InlineKeyboardMarkup(buttons)


def search_results_keyboard(files: list, query: str, offset: int, total: int, per_page: int = 10) -> InlineKeyboardMarkup:
    buttons = []
    for f in files:
        buttons.append([
            InlineKeyboardButton(
                f"📄 {f['file_name'][:35]}",
                callback_data=f"dl_{f['unique_code']}"
            )
        ])
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"search_page_{query}_{offset - per_page}"))
    if offset + per_page < total:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"search_page_{query}_{offset + per_page}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("🏠 Home", callback_data="home")])
    return InlineKeyboardMarkup(buttons)


def file_info_keyboard(unique_code: str, is_owner: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("⬇️ Download", callback_data=f"dl_{unique_code}")],
    ]
    if is_owner:
        buttons.append([InlineKeyboardButton("🗑️ Delete File", callback_data=f"del_{unique_code}")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="my_files_0")])
    return InlineKeyboardMarkup(buttons)


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton("👤 Ban User", callback_data="admin_ban"),
            InlineKeyboardButton("✅ Unban User", callback_data="admin_unban"),
        ],
        [
            InlineKeyboardButton("👑 Add Admin", callback_data="admin_addadmin"),
            InlineKeyboardButton("➖ Rem Admin", callback_data="admin_removeadmin"),
        ],
        [
            InlineKeyboardButton("📡 Add Channel", callback_data="admin_addchannel"),
            InlineKeyboardButton("🗑️ Rem Channel", callback_data="admin_removechannel"),
        ],
        [
            InlineKeyboardButton("📝 Edit Texts", callback_data="admin_edittexts"),
            InlineKeyboardButton("🗂️ Del File", callback_data="admin_deletefile"),
        ],
        [
            InlineKeyboardButton("📜 Broadcast History", callback_data="admin_bcast_history"),
        ],
        [InlineKeyboardButton("🏠 Home", callback_data="home")],
    ])


def broadcast_target_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 All Users", callback_data="bcast_target_all")],
        [InlineKeyboardButton("⭐ Premium Only", callback_data="bcast_target_premium")],
        [InlineKeyboardButton("🆓 Non-Premium", callback_data="bcast_target_non_premium")],
        [InlineKeyboardButton("👥 Referred Users", callback_data="bcast_target_referred")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")],
    ])


def broadcast_schedule_keyboard(target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Immediately", callback_data=f"bcast_schedule_now_{target}")],
        [InlineKeyboardButton("⏰ After 1 Hour", callback_data=f"bcast_schedule_1h_{target}")],
        [InlineKeyboardButton("📅 After 24 Hours", callback_data=f"bcast_schedule_24h_{target}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")],
    ])


def edit_texts_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Access Denied Msg", callback_data="edittext_access_denied")],
        [InlineKeyboardButton("✅ Verify Success Msg", callback_data="edittext_verify_success")],
        [InlineKeyboardButton("❌ Verify Failed Msg", callback_data="edittext_verify_failed")],
        [InlineKeyboardButton("📢 Join Button Text", callback_data="edittext_join_button_text")],
        [InlineKeyboardButton("👋 Welcome Message", callback_data="edittext_welcome_message")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")],
    ])
