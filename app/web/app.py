from pathlib import Path
from aiohttp import web

from app.config import config
from app.web import api, admin_api, share

MINIAPP_DIR = Path(__file__).resolve().parent.parent.parent / "miniapp"


async def health(request):
    return web.json_response({"status": "ok", "service": config.BRAND_TITLE})


async def index_app(request):
    return web.FileResponse(MINIAPP_DIR / "index.html")


async def index_admin(request):
    return web.FileResponse(MINIAPP_DIR / "admin.html")


def build_app(db, bot, bot_username: str) -> web.Application:
    app = web.Application()
    app["db"] = db
    app["bot"] = bot
    app["bot_username"] = bot_username

    app.router.add_get("/health", health)
    app.router.add_get("/api/health", health)

    app.add_routes(api.routes)
    app.add_routes(admin_api.routes)
    app.add_routes(share.routes)

    if config.ENABLE_MINI_APP:
        app.router.add_get("/app", index_app)
        app.router.add_get("/admin", index_admin)
        app.router.add_static("/static", MINIAPP_DIR, show_index=False)

    return app
