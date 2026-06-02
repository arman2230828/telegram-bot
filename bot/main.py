import asyncio
import logging
import os
import sys

from pyrogram import Client

from bot.config import API_ID, API_HASH, BOT_TOKEN
from bot import database as db
from bot.handlers.start import register_start_handlers
from bot.handlers.upload import register_upload_handlers
from bot.handlers.download import register_download_handlers
from bot.handlers.search import register_search_handlers
from bot.handlers.myfiles import register_myfiles_handlers
from bot.handlers.referral import register_referral_handlers
from bot.admin.admin import register_admin_handlers
from bot.admin.stats import register_stats_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot/logs/bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def set_bot_username(app: Client):
    from bot import config
    from bot.config import STORAGE_CHANNEL_ID
    me = await app.get_me()
    config.BOT_USERNAME = me.username or ""
    logger.info(f"Bot started: @{config.BOT_USERNAME} (ID: {me.id})")

    # Resolve storage channel peer into Pyrogram's cache so forwards work
    try:
        chat = await app.get_chat(STORAGE_CHANNEL_ID)
        logger.info(f"Storage channel resolved: {chat.title} ({chat.id})")
    except Exception as e:
        logger.error(
            f"⚠️  Could not resolve storage channel {STORAGE_CHANNEL_ID}: {e}\n"
            "Make sure the bot is an ADMIN in the storage channel."
        )


async def main():
    logger.info("Initializing database...")
    await db.init_db()
    logger.info("Database initialized.")

    app = Client(
        "get_free_storage_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        workdir="bot",
    )

    # Register all handlers
    register_start_handlers(app)
    register_upload_handlers(app)
    register_download_handlers(app)
    register_search_handlers(app)
    register_myfiles_handlers(app)
    register_referral_handlers(app)
    register_admin_handlers(app)
    register_stats_handlers(app)

    async with app:
        await set_bot_username(app)
        logger.info("✅ Get Free Storage Bot is running!")
        await asyncio.Event().wait()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
