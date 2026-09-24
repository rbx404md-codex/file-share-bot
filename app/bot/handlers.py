import io
import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, BufferedInputFile, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

from app.config import config
from app.database import Database
from app.bot.texts import t
from app.bot.keyboards import (
    main_menu_kb, force_join_kb, file_result_kb, file_need_join_kb, duplicate_kb,
)
from app.bot.utils import get_ftype, extract_meta, fmt_size, gen_short_token

log = logging.getLogger("rbx404.bot")
router = Router()

_db: Database | None = None

# In-memory, single-process state. Fine for a single Railway instance;
# both clear themselves within minutes and are never treated as durable.
_pending_password: dict[int, str] = {}        # uid -> file token awaiting a password reply
_pending_dup: dict[str, dict] = {}             # short token -> pending-upload details


def set_db(db: Database):
    """Called once from main.py at startup — avoids relying on being able to
    stash attributes on the aiogram Bot instance, which isn't guaranteed
    across aiogram versions."""
    global _db
    _db = db


def get_db(bot: Bot) -> Database:
    return _db


async def user_lang(db: Database, uid: int) -> str:
    u = await db.get_user(uid)
    return (u or {}).get("lang") or config.DEFAULT_LANGUAGE


async def check_force_join(bot: Bot, db: Database, uid: int):
    """Returns (ok: bool, missing: list[dict]) against the global force-join list."""
    if not config.ENABLE_FORCE_JOIN:
        return True, []
    channels = await db.list_force_join(enabled_only=True)
    if not channels:
        return True, []
    missing = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=uid)
            if member.status in ("left", "kicked"):
                missing.append(ch)
        except Exception:
            missing.append(ch)
    return (len(missing) == 0), missing


@router.message(CommandStart())
async def cmd_start(msg: Message, command: CommandObject):
    db = get_db(msg.bot)
    is_new = await db.add_user(msg.from_user.id, msg.from_user.full_name or "",
                                msg.from_user.username or "")
    if await db.is_banned(msg.from_user.id):
        lang = await user_lang(db, msg.from_user.id)
        await msg.answer(t(lang, "banned"))
        return

    lang = await user_lang(db, msg.from_user.id)
    ok, missing = await check_force_join(msg.bot, db, msg.from_user.id)
    if not ok:
        await msg.answer(t(lang, "not_verified"), reply_markup=force_join_kb(lang, missing))
        return

    payload = command.args
    if payload:
        await _resolve_deep_link(msg, db, lang, payload)
        return

    await msg.answer(
        t(lang, "welcome", name=msg.from_user.first_name or "there"),
        reply_markup=main_menu_kb(lang, config.BASE_URL),
    )


async def _resolve_deep_link(msg: Message, db: Database, lang: str, payload: str):
    if payload.startswith("f_"):
        fid = payload[2:]
        await deliver_file(msg, db, lang, fid)
    elif payload.startswith("c_"):
        cid = payload[2:]
        col = await db.get_collection(cid)
        if not col:
            await msg.answer(t(lang, "file_gone"))
            return
        files = await db.collection_files(cid)
        import html as _html
        await msg.answer(f"📦 <b>{_html.escape(col['name'])}</b>\n{len(files)} file(s)",
                          reply_markup=main_menu_kb(lang, config.BASE_URL))
        for f in files[:20]:
            await deliver_file(msg, db, lang, f["id"], silent_header=True)
    else:
        await msg.answer(t(lang, "welcome", name=msg.from_user.first_name or "there"),
                          reply_markup=main_menu_kb(lang, config.BASE_URL))


async def deliver_file(msg: Message, db: Database, lang: str, fid: str, silent_header=False):
    f = await db.get_file(fid)
    if not f or f.get("disabled"):
        await msg.answer(t(lang, "file_disabled" if (f and f.get("disabled")) else "file_gone"))
        return
    if f.get("download_limit") and f["downloads"] >= f["download_limit"]:
        await msg.answer(t(lang, "file_limit"))
        return
    if f.get("force_join"):
        try:
            member = await msg.bot.get_chat_member(f["force_join"], msg.from_user.id)
            if member.status in ("left", "kicked"):
                raise ValueError()
        except Exception:
            await msg.answer(
                t(lang, "need_join_file", ch=f["force_join"]),
                reply_markup=file_need_join_kb(lang, f"https://t.me/{str(f['force_join']).lstrip('@')}"),
            )
            return
    if f.get("password"):
        _pending_password[msg.from_user.id] = fid
        await msg.answer(t(lang, "enter_password"))
        return

    await _do_deliver(msg, db, f)


async def _do_deliver(msg: Message, db: Database, f: dict):
    """Actual copy + counters, after every access check has already passed."""
    try:
        await msg.bot.copy_message(msg.chat.id, config.FILE_CHANNEL, f["message_id"])
    except Exception as e:
        log.warning(f"deliver_file copy failed for {f['id']}: {e}")
        lang = await user_lang(db, msg.from_user.id)
        await msg.answer(t(lang, "file_gone"))
        return

    await db.touch_view(f["id"])
    await db.touch_download(f["id"])
    await db.inc_dl(f["user_id"])
    if f.get("one_time"):
        await db.update_file(f["id"], disabled=1)


@router.message(Command("help"))
async def cmd_help(msg: Message):
    db = get_db(msg.bot)
    lang = await user_lang(db, msg.from_user.id)
    await msg.answer(t(lang, "help"))


@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    db = get_db(msg.bot)
    lang = await user_lang(db, msg.from_user.id)
    if msg.from_user.id not in config.ADMIN_IDS:
        await msg.answer(t(lang, "admin_only"))
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👑 Admin Dashboard",
                              web_app=WebAppInfo(url=f"{config.BASE_URL}/admin"))
    ]])
    await msg.answer("👑 <b>RBX404 Admin</b>", reply_markup=kb)


@router.callback_query(F.data == "verify_join")
async def cb_verify_join(cq: CallbackQuery):
    db = get_db(cq.bot)
    lang = await user_lang(db, cq.from_user.id)
    ok, missing = await check_force_join(cq.bot, db, cq.from_user.id)
    if ok:
        await cq.message.edit_text(t(lang, "verify_ok"))
        await cq.message.answer(
            t(lang, "welcome", name=cq.from_user.first_name or "there"),
            reply_markup=main_menu_kb(lang, config.BASE_URL),
        )
    else:
        await cq.answer(t(lang, "verify_fail"), show_alert=True)


@router.callback_query(F.data.startswith("qr:"))
async def cb_qr(cq: CallbackQuery):
    if not config.ENABLE_QR:
        await cq.answer()
        return
    import qrcode
    token = cq.data.split(":", 1)[1]
    url = f"{config.BASE_URL}/share/{token}"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    await cq.message.answer_photo(
        BufferedInputFile(buf.read(), filename="qr.png"),
        caption=f"▣ {url}",
    )
    await cq.answer()


@router.callback_query(F.data.startswith("dupu:"))
async def cb_dup_use_existing(cq: CallbackQuery):
    db = get_db(cq.bot)
    lang = await user_lang(db, cq.from_user.id)
    token = cq.data.split(":", 1)[1]
    pending = _pending_dup.pop(token, None)
    if not pending:
        await cq.answer()
        return
    try:
        await cq.bot.delete_message(config.FILE_CHANNEL, pending["fwd_message_id"])
    except Exception:
        pass
    existing = await db.get_file(pending["existing_fid"])
    if not existing:
        await cq.message.edit_text(t(lang, "file_gone"))
        return
    await cq.message.edit_text(
        t(lang, "file_saved", name=existing["file_name"], size=fmt_size(existing["size"])),
        reply_markup=file_result_kb(lang, config.BASE_URL, existing["id"], config.ENABLE_QR),
    )
    await cq.message.answer(f"<code>{config.BASE_URL}/share/{existing['id']}</code>")
    await cq.answer()


@router.callback_query(F.data.startswith("dupn:"))
async def cb_dup_upload_new(cq: CallbackQuery):
    db = get_db(cq.bot)
    lang = await user_lang(db, cq.from_user.id)
    token = cq.data.split(":", 1)[1]
    pending = _pending_dup.pop(token, None)
    if not pending:
        await cq.answer()
        return
    fid = await db.add_file(
        uid=pending["uid"], message_id=pending["fwd_message_id"], file_name=pending["name"],
        file_type=pending["ftype"], size=pending["size"], caption=pending.get("caption"),
    )
    await db.log_activity(pending["uid"], "upload", fid, pending["name"])
    await cq.message.edit_text(
        t(lang, "file_saved", name=pending["name"], size=fmt_size(pending["size"])),
        reply_markup=file_result_kb(lang, config.BASE_URL, fid, config.ENABLE_QR),
    )
    await cq.message.answer(f"<code>{config.BASE_URL}/share/{fid}</code>")
    await cq.answer()


@router.message(F.content_type.in_({
    "document", "video", "photo", "audio", "voice", "animation", "sticker",
}))
async def handle_upload(msg: Message):
    db = get_db(msg.bot)
    lang = await user_lang(db, msg.from_user.id)

    if await db.is_banned(msg.from_user.id):
        await msg.answer(t(lang, "banned"))
        return
    ok, missing = await check_force_join(msg.bot, db, msg.from_user.id)
    if not ok:
        await msg.answer(t(lang, "not_verified"), reply_markup=force_join_kb(lang, missing))
        return

    ftype = get_ftype(msg)
    name, size, _ = extract_meta(msg, ftype)

    try:
        fwd = await msg.forward(config.FILE_CHANNEL)
    except Exception as e:
        log.error(f"forward to FILE_CHANNEL failed: {e}")
        await msg.answer("❌ Storage channel isn't reachable — check FILE_CHANNEL / bot admin rights.")
        return

    dup = await db.find_duplicate(msg.from_user.id, name, size)
    if dup:
        token = gen_short_token()
        _pending_dup[token] = {
            "uid": msg.from_user.id, "fwd_message_id": fwd.message_id, "ftype": ftype,
            "name": name, "size": size, "caption": msg.caption, "existing_fid": dup["id"],
        }
        await msg.answer(
            t(lang, "dup_found", name=name, size=fmt_size(size)),
            reply_markup=duplicate_kb(lang, token),
        )
        return

    fid = await db.add_file(
        uid=msg.from_user.id, message_id=fwd.message_id, file_name=name,
        file_type=ftype, size=size, caption=msg.caption,
    )
    await db.log_activity(msg.from_user.id, "upload", fid, name)

    await msg.answer(
        t(lang, "file_saved", name=name, size=fmt_size(size)),
        reply_markup=file_result_kb(lang, config.BASE_URL, fid, config.ENABLE_QR),
    )
    share_url = f"{config.BASE_URL}/share/{fid}"
    await msg.answer(f"<code>{share_url}</code>")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(msg: Message):
    db = get_db(msg.bot)
    lang = await user_lang(db, msg.from_user.id)
    if await db.is_banned(msg.from_user.id):
        await msg.answer(t(lang, "banned"))
        return

    # A reply to a "🔒 enter password" prompt takes priority over treating
    # this text as a brand-new shareable message.
    pending_fid = _pending_password.pop(msg.from_user.id, None)
    if pending_fid:
        f = await db.get_file(pending_fid)
        if not f:
            await msg.answer(t(lang, "file_gone"))
            return
        if (msg.text or "").strip() != (f.get("password") or ""):
            await msg.answer(t(lang, "wrong_password"))
            return
        await _do_deliver(msg, db, f)
        return

    ok, missing = await check_force_join(msg.bot, db, msg.from_user.id)
    if not ok:
        await msg.answer(t(lang, "not_verified"), reply_markup=force_join_kb(lang, missing))
        return

    try:
        fwd = await msg.forward(config.FILE_CHANNEL)
    except Exception as e:
        log.error(f"forward text to FILE_CHANNEL failed: {e}")
        return

    fid = await db.add_file(
        uid=msg.from_user.id, message_id=fwd.message_id,
        file_name=(msg.text[:60] if msg.text else "Text"), file_type="text",
        size=len(msg.text or ""),
    )
    await db.log_activity(msg.from_user.id, "upload", fid, "Text message")
    await msg.answer(
        t(lang, "file_saved", name="Text message", size=fmt_size(len(msg.text or ""))),
        reply_markup=file_result_kb(lang, config.BASE_URL, fid, config.ENABLE_QR),
    )
    await msg.answer(f"<code>{config.BASE_URL}/share/{fid}</code>")
