import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
OWNER_ID = int(os.environ.get("OWNER_ID", 0))
_raw_storage = os.environ.get("STORAGE_CHANNEL_ID", "0")
try:
    STORAGE_CHANNEL_ID = int(_raw_storage)
except ValueError:
    import sys
    print(f"ERROR: STORAGE_CHANNEL_ID must be a numeric channel ID (e.g. -1001234567890), got: {_raw_storage!r}", file=sys.stderr)
    sys.exit(1)

BOT_USERNAME = ""

LOG_FILE = "bot/logs/bot.log"
MAX_RATE_LIMIT = 3
RATE_LIMIT_WINDOW = 10
