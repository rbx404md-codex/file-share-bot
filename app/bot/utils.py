import hashlib
import hmac
from urllib.parse import parse_qsl

from aiogram.types import Message


def get_ftype(msg: Message) -> str:
    if msg.document:
        return "document"
    if msg.video:
        return "video"
    if msg.photo:
        return "photo"
    if msg.audio:
        return "audio"
    if msg.voice:
        return "voice"
    if msg.animation:
        return "animation"
    if msg.sticker:
        return "sticker"
    if msg.text:
        return "text"
    return "other"


def extract_meta(msg: Message, ftype: str):
    """Returns (file_name, size, telegram_file_id_or_None)."""
    obj = {
        "document": msg.document, "video": msg.video, "audio": msg.audio,
        "voice": msg.voice, "animation": msg.animation, "sticker": msg.sticker,
    }.get(ftype)
    if ftype == "photo" and msg.photo:
        obj = msg.photo[-1]
    if obj is None:
        if ftype == "text":
            return (msg.text[:60] if msg.text else "Text message"), len(msg.text or ""), None
        return "Untitled", 0, None
    name = getattr(obj, "file_name", None) or f"{ftype}_{getattr(obj, 'file_unique_id', '')}"
    size = getattr(obj, "file_size", 0) or 0
    return name, size, getattr(obj, "file_id", None)


def fmt_size(n: int) -> str:
    n = n or 0
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def verify_webapp_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400):
    """
    Validates Telegram Mini App `initData` per Telegram's documented HMAC scheme.
    Returns the parsed data dict (with `user` as a parsed dict) on success, or
    None if the signature is invalid/expired. NEVER trust a user id that didn't
    pass this check.
    """
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None
    recv_hash = pairs.pop("hash", None)
    if not recv_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calc_hash, recv_hash):
        return None

    import time, json
    auth_date = int(pairs.get("auth_date", 0))
    if max_age_seconds and time.time() - auth_date > max_age_seconds:
        return None

    if "user" in pairs:
        try:
            pairs["user"] = json.loads(pairs["user"])
        except Exception:
            pass
    return pairs
