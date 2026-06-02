# Get Free Storage Bot

A production-ready Telegram file storage bot where users can upload any file, get a permanent shareable link, and anyone can download it instantly via deep link.

## Run & Operate

- Workflow: **Telegram Bot** — runs `python -m bot.main`
- Bot username: `@Getfreestorage_bot`
- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)

## Stack

- Python 3.12 + Pyrogram 2.0.106 + TgCrypto
- PostgreSQL + asyncpg (Replit built-in DB)
- Async modular architecture

## Where things live

- `bot/main.py` — entry point, wires up all handlers
- `bot/config.py` — env var loading
- `bot/database.py` — all DB queries (asyncpg, PostgreSQL)
- `bot/handlers/` — start, upload, download, search, myfiles, referral
- `bot/admin/` — admin panel, stats, broadcast
- `bot/keyboards/menus.py` — all inline keyboards
- `bot/utils/helpers.py` — rate limiting, file size formatting, link generation

## Required Secrets

| Key | Description |
|---|---|
| `API_ID` | From https://my.telegram.org/apps |
| `API_HASH` | From https://my.telegram.org/apps |
| `BOT_TOKEN` | From @BotFather |
| `OWNER_ID` | Your numeric Telegram user ID |
| `STORAGE_CHANNEL_ID` | Numeric ID of private storage channel (e.g. -1003449589003) |
| `DATABASE_URL` | Replit PostgreSQL (auto-provided) |

## Architecture decisions

- Files are forwarded to a private Telegram storage channel; only `file_id` + metadata stored in DB (no binary storage)
- Force-join channels are stored in DB and managed live from admin panel — no code changes needed
- All bot text messages (welcome, access denied, etc.) are stored in `bot_texts` table and editable via admin panel
- Rate limiting is in-memory per user (not Redis) — sufficient for current scale
- Broadcast runs as an `asyncio.create_task` to avoid blocking the bot

## Product

- **Upload**: Send any file → get permanent shareable link
- **Download**: Open deep link → file delivered instantly via Telegram file_id
- **Search**: Search stored files by name with pagination
- **My Files**: View, manage, and delete your uploaded files
- **Referral**: Get a referral link; track how many people you've invited
- **Admin Panel**: `/admin` — stats, broadcast, ban/unban, manage channels, edit texts, delete files

## Admin Commands

`/admin` `/stats` `/users` `/files`

## Gotchas

- `STORAGE_CHANNEL_ID` must be a **numeric ID** (e.g. `-1003449589003`), NOT an invite link
- The bot must be an **admin** in the storage channel to forward files
- The bot must be an **admin** in any force-join channels to check membership
- Session file is saved as `bot/get_free_storage_bot.session` — do not delete it

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._
