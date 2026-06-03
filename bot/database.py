import asyncpg
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=2, max_size=10)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                join_date TIMESTAMP DEFAULT NOW(),
                total_uploads INTEGER DEFAULT 0,
                referral_count INTEGER DEFAULT 0,
                total_downloads INTEGER DEFAULT 0,
                is_banned BOOLEAN DEFAULT FALSE,
                is_premium BOOLEAN DEFAULT FALSE
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id SERIAL PRIMARY KEY,
                unique_code TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT DEFAULT 'document',
                file_size BIGINT DEFAULT 0,
                uploader_id BIGINT NOT NULL,
                upload_date TIMESTAMP DEFAULT NOW(),
                download_count INTEGER DEFAULT 0
            )
        """)
        # Migrate existing tables that may not have file_type column
        await conn.execute("""
            ALTER TABLE files ADD COLUMN IF NOT EXISTS file_type TEXT DEFAULT 'document'
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id SERIAL PRIMARY KEY,
                referrer_id BIGINT NOT NULL,
                referred_id BIGINT NOT NULL UNIQUE,
                join_date TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                admin_id BIGINT PRIMARY KEY,
                added_date TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS force_join_channels (
                channel_id TEXT PRIMARY KEY,
                channel_username TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_texts (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_history (
                id SERIAL PRIMARY KEY,
                message_content TEXT,
                sent_at TIMESTAMP DEFAULT NOW(),
                total_delivered INTEGER DEFAULT 0,
                total_failed INTEGER DEFAULT 0,
                target_group TEXT DEFAULT 'all'
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_queue (
                id SERIAL PRIMARY KEY,
                message TEXT NOT NULL,
                target_group TEXT DEFAULT 'all',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_uploader ON files(uploader_id);
            CREATE INDEX IF NOT EXISTS idx_files_unique_code ON files(unique_code);
            CREATE INDEX IF NOT EXISTS idx_files_name ON files(file_name);
        """)
        default_texts = [
            ("access_denied", "🚫 <b>Access Denied</b>\n\nYou must join all required channels to use this bot.\n\nAfter joining, click ✅ I Joined."),
            ("verify_success", "✅ <b>Verification successful!</b>\n\nYou can now use the bot."),
            ("verify_failed", "❌ <b>Verification failed!</b>\n\nYou must join all required channels before using this bot."),
            ("join_button_text", "📢 Join Channel"),
            ("welcome_message", "👋 <b>Welcome to Get Free Storage!</b>\n\nStore your files safely on Telegram.\n\n<b>Supported Files:</b>\n• APK • ZIP • PDF\n• Video • Audio • Images • Documents\n\n<b>Features:</b>\n✅ Permanent Storage\n⚡ Fast Downloads\n🔐 Secure Links\n🎁 Referral Rewards\n🔗 Unlimited Sharing\n\nUpload a file to begin."),
        ]
        for key, value in default_texts:
            await conn.execute(
                "INSERT INTO bot_texts (key, value) VALUES ($1, $2) ON CONFLICT (key) DO NOTHING",
                key, value
            )
    logger.info("Database initialized successfully")


async def get_user(user_id: int):
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)


async def upsert_user(user_id: int, username: str, first_name: str):
    pool = await get_pool()
    await pool.execute("""
        INSERT INTO users (user_id, username, first_name)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id) DO UPDATE SET username = $2, first_name = $3
    """, user_id, username, first_name)


async def is_banned(user_id: int) -> bool:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT is_banned FROM users WHERE user_id = $1", user_id)
    return row["is_banned"] if row else False


async def ban_user(user_id: int):
    pool = await get_pool()
    await pool.execute("UPDATE users SET is_banned = TRUE WHERE user_id = $1", user_id)


async def unban_user(user_id: int):
    pool = await get_pool()
    await pool.execute("UPDATE users SET is_banned = FALSE WHERE user_id = $1", user_id)


async def is_admin(user_id: int) -> bool:
    from bot.config import OWNER_ID
    if user_id == OWNER_ID:
        return True
    pool = await get_pool()
    row = await pool.fetchrow("SELECT admin_id FROM admins WHERE admin_id = $1", user_id)
    return row is not None


async def add_admin(admin_id: int):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO admins (admin_id) VALUES ($1) ON CONFLICT DO NOTHING", admin_id
    )


async def remove_admin(admin_id: int):
    pool = await get_pool()
    await pool.execute("DELETE FROM admins WHERE admin_id = $1", admin_id)


async def get_force_join_channels():
    pool = await get_pool()
    return await pool.fetch("SELECT * FROM force_join_channels")


async def add_force_join_channel(channel_id: str, channel_username: str = None):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO force_join_channels (channel_id, channel_username) VALUES ($1, $2) ON CONFLICT DO NOTHING",
        channel_id, channel_username
    )


async def remove_force_join_channel(channel_id: str):
    pool = await get_pool()
    await pool.execute("DELETE FROM force_join_channels WHERE channel_id = $1", channel_id)


async def save_file(unique_code: str, file_name: str, file_id: str, file_size: int, uploader_id: int, file_type: str = "document"):
    pool = await get_pool()
    await pool.execute("""
        INSERT INTO files (unique_code, file_name, file_id, file_type, file_size, uploader_id)
        VALUES ($1, $2, $3, $4, $5, $6)
    """, unique_code, file_name, file_id, file_type, file_size, uploader_id)
    await pool.execute("UPDATE users SET total_uploads = total_uploads + 1 WHERE user_id = $1", uploader_id)


async def get_file_by_code(unique_code: str):
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM files WHERE unique_code = $1", unique_code)


async def increment_download_count(unique_code: str, downloader_id: int):
    pool = await get_pool()
    await pool.execute("UPDATE files SET download_count = download_count + 1 WHERE unique_code = $1", unique_code)
    await pool.execute("UPDATE users SET total_downloads = total_downloads + 1 WHERE user_id = $1", downloader_id)


async def get_user_files(user_id: int, offset: int = 0, limit: int = 10):
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM files WHERE uploader_id = $1 ORDER BY upload_date DESC LIMIT $2 OFFSET $3",
        user_id, limit, offset
    )


async def search_files(query: str, offset: int = 0, limit: int = 10):
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM files WHERE file_name ILIKE $1 ORDER BY download_count DESC LIMIT $2 OFFSET $3",
        f"%{query}%", limit, offset
    )


async def search_files_count(query: str) -> int:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT COUNT(*) FROM files WHERE file_name ILIKE $1", f"%{query}%")
    return row["count"]


async def delete_file(unique_code: str):
    pool = await get_pool()
    await pool.execute("DELETE FROM files WHERE unique_code = $1", unique_code)


async def add_referral(referrer_id: int, referred_id: int):
    pool = await get_pool()
    existing = await pool.fetchrow("SELECT id FROM referrals WHERE referred_id = $1", referred_id)
    if existing:
        return False
    await pool.execute(
        "INSERT INTO referrals (referrer_id, referred_id) VALUES ($1, $2)", referrer_id, referred_id
    )
    await pool.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = $1", referrer_id)
    return True


async def get_referral_count(user_id: int) -> int:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT referral_count FROM users WHERE user_id = $1", user_id)
    return row["referral_count"] if row else 0


async def get_stats():
    pool = await get_pool()
    total_users = await pool.fetchval("SELECT COUNT(*) FROM users")
    total_files = await pool.fetchval("SELECT COUNT(*) FROM files")
    total_downloads = await pool.fetchval("SELECT COALESCE(SUM(download_count), 0) FROM files")
    premium_users = await pool.fetchval("SELECT COUNT(*) FROM users WHERE is_premium = TRUE")
    today = datetime.utcnow().date()
    daily_uploads = await pool.fetchval(
        "SELECT COUNT(*) FROM files WHERE DATE(upload_date) = $1", today
    )
    daily_joins = await pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE DATE(join_date) = $1", today
    )
    return {
        "total_users": total_users,
        "total_files": total_files,
        "total_downloads": total_downloads,
        "premium_users": premium_users,
        "daily_uploads": daily_uploads,
        "daily_joins": daily_joins,
    }


async def get_all_user_ids(target: str = "all"):
    pool = await get_pool()
    if target == "premium":
        rows = await pool.fetch("SELECT user_id FROM users WHERE is_premium = TRUE AND is_banned = FALSE")
    elif target == "non_premium":
        rows = await pool.fetch("SELECT user_id FROM users WHERE is_premium = FALSE AND is_banned = FALSE")
    elif target == "referred":
        rows = await pool.fetch("SELECT DISTINCT referred_id AS user_id FROM referrals")
    else:
        rows = await pool.fetch("SELECT user_id FROM users WHERE is_banned = FALSE")
    return [r["user_id"] for r in rows]


async def save_broadcast(message_content: str, delivered: int, failed: int, target: str):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO broadcast_history (message_content, total_delivered, total_failed, target_group) VALUES ($1, $2, $3, $4)",
        message_content, delivered, failed, target
    )


async def get_broadcast_history():
    pool = await get_pool()
    return await pool.fetch("SELECT * FROM broadcast_history ORDER BY sent_at DESC LIMIT 10")


async def get_bot_text(key: str) -> str:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT value FROM bot_texts WHERE key = $1", key)
    return row["value"] if row else ""


async def set_bot_text(key: str, value: str):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO bot_texts (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = $2",
        key, value
    )
