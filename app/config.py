"""
Central configuration for RBX404 Digital File Platform.

Everything sensitive comes from environment variables only — nothing is
hardcoded here. BASE_URL is auto-derived from Railway's public-domain
variables when the app is deployed there, so no custom domain is required.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _env_int(name, default=None):
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _env_int_list(name, default=None):
    v = os.environ.get(name)
    if not v:
        return default or []
    out = []
    for part in v.split(","):
        part = part.strip()
        if part:
            try:
                out.append(int(part))
            except ValueError:
                pass
    return out


def _env_bool(name, default=False):
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _detect_base_url() -> str:
    """
    Priority:
      1. Explicit BASE_URL from .env / Railway variables (manual override).
      2. RAILWAY_PUBLIC_DOMAIN — set automatically by Railway when a public
         domain (their free generated one, or a custom one) is attached.
      3. RAILWAY_STATIC_URL — older Railway variable, kept as a fallback.
      4. Local dev fallback (http://localhost:PORT) — Telegram will reject
         this for a real Mini App button, but it keeps local runs from
         crashing while you set up a tunnel.
    """
    explicit = os.environ.get("BASE_URL", "").strip().rstrip("/")
    if explicit:
        return explicit

    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if railway_domain:
        return f"https://{railway_domain}"

    legacy = os.environ.get("RAILWAY_STATIC_URL", "").strip()
    if legacy:
        return legacy if legacy.startswith("http") else f"https://{legacy}"

    port = os.environ.get("PORT", "8080")
    return f"http://localhost:{port}"


class Config:
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
    ADMIN_IDS = _env_int_list("ADMIN_IDS", [])
    FILE_CHANNEL = _env_int("FILE_CHANNEL")
    LOG_CHANNEL = _env_int("LOG_CHANNEL")
    BACKUP_CHANNEL = _env_int("BACKUP_CHANNEL") or FILE_CHANNEL

    DATABASE_PATH = os.environ.get("DATABASE_PATH", "data/rbx404.db")

    BASE_URL = _detect_base_url()
    PORT = _env_int("PORT", 8080)

    SIGNING_SECRET = os.environ.get("SIGNING_SECRET", "").strip()

    BRAND_NAME = os.environ.get("BRAND_NAME", "RBX404")
    BRAND_TITLE = os.environ.get("BRAND_TITLE", "RBX404 Digital File Platform")
    DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "bn")

    ENABLE_MINI_APP = _env_bool("ENABLE_MINI_APP", True)
    ENABLE_QR = _env_bool("ENABLE_QR", True)
    ENABLE_FORCE_JOIN = _env_bool("ENABLE_FORCE_JOIN", True)

    TRASH_RETENTION_DAYS = _env_int("TRASH_RETENTION_DAYS", 7)
    DEFAULT_AUTO_DELETE_MINUTES = _env_int("DEFAULT_AUTO_DELETE_MINUTES", 0)

    @classmethod
    def validate(cls):
        problems = []
        if not cls.BOT_TOKEN:
            problems.append("BOT_TOKEN is not set.")
        if not cls.FILE_CHANNEL:
            problems.append("FILE_CHANNEL is not set (numeric channel id the bot can post to).")
        if not cls.ADMIN_IDS:
            problems.append("ADMIN_IDS is empty — no one will be able to reach /admin.")
        if not cls.SIGNING_SECRET:
            problems.append("SIGNING_SECRET is not set — Mini App auth will refuse to start.")
        return problems


config = Config()
