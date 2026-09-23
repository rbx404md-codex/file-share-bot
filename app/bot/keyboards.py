from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
)
from app.config import config
from app.bot.texts import t


def main_menu_kb(lang, base_url):
    rows = [
        [InlineKeyboardButton(text=t(lang, "open_app"),
                               web_app=WebAppInfo(url=f"{base_url}/app"))],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def force_join_kb(lang, channels):
    rows = []
    for ch in channels:
        rows.append([InlineKeyboardButton(text=f"📢 {ch['title'] or ch['chat_id']}", url=ch["url"])])
    rows.append([InlineKeyboardButton(text=t(lang, "verify_btn"), callback_data="verify_join")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def file_result_kb(lang, base_url, token, enable_qr=True):
    rows = [
        [InlineKeyboardButton(text=t(lang, "settings"),
                               web_app=WebAppInfo(url=f"{base_url}/app#file/{token}"))],
    ]
    if enable_qr:
        rows[0].append(InlineKeyboardButton(text=t(lang, "qr_code"), callback_data=f"qr:{token}"))
    rows.append([InlineKeyboardButton(text=t(lang, "open_app"),
                                       web_app=WebAppInfo(url=f"{base_url}/app"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def file_need_join_kb(lang, url):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Join", url=url)],
    ])
