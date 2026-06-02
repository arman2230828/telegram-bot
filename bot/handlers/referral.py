import logging
from pyrogram import Client, enums, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot import database as db
from bot.utils.helpers import get_referral_link
from bot.keyboards.menus import back_to_home

logger = logging.getLogger(__name__)


def register_referral_handlers(app: Client):

    @app.on_callback_query(filters.regex("^referral$"))
    async def referral_callback(client: Client, query: CallbackQuery):
        from bot.config import BOT_USERNAME
        user_id = query.from_user.id
        user = await db.get_user(user_id)

        referral_count = user["referral_count"] if user else 0
        ref_link = get_referral_link(BOT_USERNAME, user_id)
        share_link = f"https://t.me/share/url?url={ref_link}&text=Join+this+amazing+file+storage+bot!"

        await query.message.edit_text(
            f"👥 <b>Referral Dashboard</b>\n\n"
            f"👤 <b>Total Referrals:</b> {referral_count}\n\n"
            f"🔗 <b>Your Referral Link:</b>\n<code>{ref_link}</code>\n\n"
            f"Share your link to invite friends. Each person who joins counts as a referral!",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Share Referral Link", url=share_link)],
                [InlineKeyboardButton("🏠 Home", callback_data="home")],
            ])
        )
