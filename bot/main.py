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

    try:
        chat = await app.get_chat(STORAGE_CHANNEL_ID)
        logger.info(f"✅ Storage channel resolved: {chat.title} ({chat.id})")
    except Exception as e:
        logger.warning(
            f"Storage channel peer not cached yet ({e}). "
            "Uploads will still work using original file_ids."
        )


async def process_broadcast_queue(app: Client):
    """Poll broadcast_queue table every 15 seconds and process pending items."""
    from pyrogram import enums
    while True:
        try:
            pool = await db.get_pool()
            row = await pool.fetchrow(
                "SELECT * FROM broadcast_queue WHERE status='pending' ORDER BY created_at LIMIT 1"
            )
            if row:
                await pool.execute(
                    "UPDATE broadcast_queue SET status='running' WHERE id=$1", row["id"]
                )
                user_ids = await db.get_all_user_ids(row["target_group"])
                delivered = 0
                failed = 0
                for uid in user_ids:
                    try:
                        await asyncio.sleep(0.05)
                        await app.send_message(uid, row["message"], parse_mode=enums.ParseMode.HTML)
                        delivered += 1
                    except Exception:
                        failed += 1

                await pool.execute(
                    "UPDATE broadcast_queue SET status='done' WHERE id=$1", row["id"]
                )
                await db.save_broadcast(row["message"], delivered, failed, row["target_group"])
                logger.info(f"Web broadcast done: {delivered} delivered, {failed} failed")
        except Exception as e:
            logger.error(f"Broadcast queue error: {e}")

        await asyncio.sleep(15)


async def start_web_admin():
    """Start the web admin panel FastAPI server."""
    try:
        import uvicorn
        from bot.web_admin.server import app as web_app
        port = int(os.environ.get("ADMIN_PORT", 8080))
        config = uvicorn.Config(
            web_app,
            host="0.0.0.0",
            port=port,
            log_level="warning",
            access_log=False,
        )
        server = uvicorn.Server(config)
        logger.info(f"✅ Web Admin Panel started on port {port}")
        await server.serve()
    except ImportError:
        logger.warning(
            "uvicorn/fastapi not installed. Web admin panel disabled.\n"
            "Install with: pip install fastapi uvicorn"
        )
    except Exception as e:
        logger.error(f"Web admin panel error: {e}")


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

    # Admin handlers MUST be registered BEFORE upload handlers
    # to allow stop_propagation() to work correctly
    register_admin_handlers(app)
    register_stats_handlers(app)
    register_start_handlers(app)
    register_upload_handlers(app)
    register_download_handlers(app)
    register_search_handlers(app)
    register_myfiles_handlers(app)
    register_referral_handlers(app)

    async with app:
        await set_bot_username(app)
        logger.info("✅ Get Free Storage Bot is running!")

        # Run web admin + broadcast queue poller concurrently with the bot
        await asyncio.gather(
            asyncio.Event().wait(),          # Keep bot alive
            start_web_admin(),               # Web admin panel
            process_broadcast_queue(app),    # Web broadcast queue
        )


if __name__ == "__main__":
    asyncio.run(main())
