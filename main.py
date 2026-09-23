import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from app.config import config
from app.database import Database
from app.bot.handlers import router as bot_router, set_db as set_bot_db
from app.web.app import build_app

logging.basicConfig(level=logging.INFO,
                     format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("rbx404.main")


async def expiry_cleanup_loop(bot: Bot, db: Database):
    """Background task: expire files, warn owners ~1h before expiry, purge old trash."""
    while True:
        try:
            for f in await db.soon_expiring(window_seconds=3600):
                await db.mark_expiry_notified(f["id"])
                u = await db.get_user(f["user_id"])
                if u and u.get("notify", 1):
                    try:
                        await bot.send_message(
                            f["user_id"],
                            f"⏳ <b>{f['file_name']}</b> will expire soon.",
                        )
                    except Exception:
                        pass

            for fid in await db.expired_file_ids():
                f = await db.get_file(fid, include_deleted=True)
                if not f:
                    continue
                try:
                    await bot.delete_message(config.FILE_CHANNEL, f["message_id"])
                except Exception:
                    pass
                await db.delete_file_permanent(fid)
                if config.LOG_CHANNEL:
                    try:
                        await bot.send_message(config.LOG_CHANNEL,
                                                f"⏳ Expired file cleaned up: {f['file_name']}")
                    except Exception:
                        pass

            purged = await db.purge_old_trash(days=config.TRASH_RETENTION_DAYS)
            if purged and config.LOG_CHANNEL:
                try:
                    await bot.send_message(
                        config.LOG_CHANNEL,
                        f"🧹 Auto-purged {len(purged)} trashed file(s) "
                        f"(past {config.TRASH_RETENTION_DAYS}-day retention)",
                    )
                except Exception:
                    pass
        except Exception as e:
            log.error(f"expiry_cleanup_loop error: {e}")
        await asyncio.sleep(300)


async def main():
    problems = config.validate()
    if problems:
        log.error("Configuration problems:\n  - " + "\n  - ".join(problems))
        if not config.BOT_TOKEN or not config.FILE_CHANNEL:
            log.error("Cannot start without BOT_TOKEN and FILE_CHANNEL. Exiting.")
            return

    Path(config.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)

    db = Database(config.DATABASE_PATH)
    await db.connect()
    log.info(f"Database ready at {config.DATABASE_PATH}")

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    set_bot_db(db)  # make the database available to bot handlers
    me = await bot.get_me()
    log.info(f"Bot @{me.username} starting...")
    log.info(f"Base URL: {config.BASE_URL}")

    dp = Dispatcher()
    dp.include_router(bot_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Start / open the platform"),
        types.BotCommand(command="help", description="Get help"),
        types.BotCommand(command="admin", description="Admin dashboard (admins only)"),
    ])

    web_app = build_app(db, bot, me.username)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.PORT)
    await site.start()
    log.info(f"Web server listening on 0.0.0.0:{config.PORT}")

    cleanup_task = asyncio.create_task(expiry_cleanup_loop(bot, db))

    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        cleanup_task.cancel()
        await runner.cleanup()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
