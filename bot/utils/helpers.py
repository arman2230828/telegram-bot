-import random
import string
import time
from collections import defaultdict

_rate_limits: dict = defaultdict(list)


def generate_unique_code(length: int = 8) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    else:
        return f"{size_bytes / 1024 ** 3:.2f} GB"


def check_rate_limit(user_id: int, max_calls: int = 3, window: int = 10) -> bool:
    now = time.time()
    calls = _rate_limits[user_id]
    _rate_limits[user_id] = [t for t in calls if now - t < window]
    if len(_rate_limits[user_id]) >= max_calls:
        return False
    _rate_limits[user_id].append(now)
    return True


def get_deep_link(bot_username: str, code: str) -> str:
    return f"https://t.me/{bot_username}?start=file_{code}"


def get_referral_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{user_id}"
