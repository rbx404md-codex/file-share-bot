from aiohttp import web
from app.config import config
from app.bot.utils import verify_webapp_init_data


def require_user(handler):
    """
    Decorator for aiohttp handlers: validates the `X-Telegram-Init-Data` header
    against BOT_TOKEN per Telegram's HMAC scheme and injects `request["uid"]`.
    Never trusts a plain user-id sent by the frontend JS.
    """
    async def wrapped(request: web.Request):
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        data = verify_webapp_init_data(init_data, config.BOT_TOKEN)
        if not data or "user" not in data:
            return web.json_response({"error": "unauthorized"}, status=401)
        request["uid"] = int(data["user"]["id"])
        request["tg_user"] = data["user"]
        db = request.app["db"]
        if await db.is_banned(request["uid"]):
            return web.json_response({"error": "banned"}, status=403)
        return await handler(request)
    return wrapped


def require_admin(handler):
    async def wrapped(request: web.Request):
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        data = verify_webapp_init_data(init_data, config.BOT_TOKEN)
        if not data or "user" not in data:
            return web.json_response({"error": "unauthorized"}, status=401)
        uid = int(data["user"]["id"])
        if uid not in config.ADMIN_IDS:
            return web.json_response({"error": "forbidden"}, status=403)
        request["uid"] = uid
        request["tg_user"] = data["user"]
        return await handler(request)
    return wrapped
