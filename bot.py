#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ============================================================
# Project Name : File Shear Bot Telegram 
#
# Developer    : @robiulxxxxxxx
# Telegram     : https://t.me/SkillShareBDCommunity
# The author is not responsible for any misuse, abuse,
# damages, or violations caused by this software.
#
# Use this project at your own risk.
# ============================================================

import json, os, asyncio, datetime, logging, string, random, html, io
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    BufferedInputFile, CallbackQuery, Message,
    ChatMemberOwner, ChatMemberAdministrator, ChatMemberMember
)
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.client.default import DefaultBotProperties

# ═══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════

BOT_TOKEN = "8631065484:AAH7NipvhHUqXFJ4vnCeyEiMk6sI6lmNoQ4"
FILE_CHANNEL = -1003820862559
BACKUP_CHANNEL = -1003820862559
ADMIN_IDS = [7294948308, 7370387694]
BOT_USERNAME = "NebulaShareBot"
DB_FILE = Path(__file__).parent / "database.json"
SUPPORT_CHANNEL = "https://t.me/Silent_Reaper_x"
ADMIN_CONTACT = "@robiulxxxxxxx"
DEFAULT_AUTO_DELETE = 20  # minutes

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
logging.getLogger("aiogram").setLevel(logging.WARNING)
log = logging.getLogger("bot")

# ═══════════════════════════════════════════════════════════════
#  STYLED BUTTON BUILDER
# ═══════════════════════════════════════════════════════════════

def btn(text: str, callback_data: str = None, url: str = None,
        style: str = None, icon: str = None) -> InlineKeyboardButton:
    if style is None:
        style = "primary"
    kwargs = {"text": text}
    if callback_data: kwargs["callback_data"] = callback_data
    if url: kwargs["url"] = url
    
    b = InlineKeyboardButton(**kwargs)
    if hasattr(b, '__pydantic_extra__'):
        if b.__pydantic_extra__ is None:
            b.__pydantic_extra__ = {}
        if style: b.__pydantic_extra__['style'] = style
        if icon: b.__pydantic_extra__['icon_custom_emoji_id'] = icon
    return b

S_DANGER = "danger"
S_SUCCESS = "success"
S_PRIMARY = "primary"

# ═══════════════════════════════════════════════════════════════
#  TEXT STYLING
# ═══════════════════════════════════════════════════════════════

def sc(t): return t.translate(str.maketrans('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', 'ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ'))
def bf(t): return t.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', '𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗'))
def esc(t): return html.escape(str(t)) if t else ""

def gen_id(n=10): return ''.join(random.choices(string.ascii_letters + string.digits, k=n))
def now_iso(): return datetime.datetime.utcnow().isoformat()
def fmt_dt(iso):
    try: return datetime.datetime.fromisoformat(iso).strftime("%d %b %Y, %H:%M UTC")
    except: return str(iso)

# ═══════════════════════════════════════════════════════════════
#  DATABASE
# ═══════════════════════════════════════════════════════════════

class DB:
    def __init__(self, fp):
        self.fp = fp
        self.d = self._load()

    def _load(self):
        if os.path.exists(self.fp):
            try:
                with open(self.fp, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {"users": {}, "files": {}, "settings": {"auto_delete_minutes": DEFAULT_AUTO_DELETE, "admins": []}, "banned": []}

    def save(self):
        tmp = str(self.fp) + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, str(self.fp))

    def add_user(self, uid, name=""):
        k = str(uid)
        if k not in self.d["users"]:
            self.d["users"][k] = {"lang":"","name":name,"join_date":now_iso(),"files_count":0,"total_downloads":0}
            self.save()
            return True
        if name and self.d["users"][k].get("name") != name:
            self.d["users"][k]["name"] = name
            self.save()
        return False

    def get_user(self, uid): return self.d["users"].get(str(uid))
    def get_lang(self, uid): return (self.get_user(uid) or {}).get("lang", "en") or "en"
    def set_lang(self, uid, lang):
        if str(uid) in self.d["users"]:
            self.d["users"][str(uid)]["lang"] = lang
            self.save()
    def all_uids(self): return [int(k) for k in self.d["users"]]
    def user_count(self): return len(self.d["users"])
    def today_users(self):
        td = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        return sum(1 for u in self.d["users"].values() if u.get("join_date","").startswith(td))
    def inc_files(self, uid):
        if str(uid) in self.d["users"]:
            self.d["users"][str(uid)]["files_count"] = self.d["users"][str(uid)].get("files_count",0)+1
            self.save()
    def inc_dl(self, uid):
        if str(uid) in self.d["users"]:
            self.d["users"][str(uid)]["total_downloads"] = self.d["users"][str(uid)].get("total_downloads",0)+1
            self.save()
    def ban(self, uid):
        if int(uid) not in self.d["banned"]:
            self.d["banned"].append(int(uid))
            self.save()
    def unban(self, uid):
        if int(uid) in self.d["banned"]:
            self.d["banned"].remove(int(uid))
            self.save()
    def is_banned(self, uid): return int(uid) in self.d["banned"]
    
    def save_file(self, fid, msg_id, uid, ftype, fname, caption, public=False):
        self.d["files"][fid] = {
            "message_id": msg_id, "user_id": int(uid), "file_type": ftype,
            "file_name": fname or "Untitled", "caption": caption or "",
            "upload_date": now_iso(), "is_public": public,
            "password": None, "force_join": None, "downloads": 0
        }
        self.inc_files(uid)
        self.save()

    def get_file(self, fid): return self.d["files"].get(fid)
    def del_file(self, fid):
        if fid in self.d["files"]:
            del self.d["files"][fid]
            self.save()
            return True
        return False
    def set_pw(self, fid, pw):
        if fid in self.d["files"]:
            self.d["files"][fid]["password"] = pw
            self.save()
    def set_public(self, fid, pub):
        if fid in self.d["files"]:
            self.d["files"][fid]["is_public"] = pub
            self.save()
    def set_caption(self, fid, cap):
        if fid in self.d["files"]:
            self.d["files"][fid]["caption"] = cap
            self.save()
    def set_fj(self, fid, ch):
        if fid in self.d["files"]:
            self.d["files"][fid]["force_join"] = ch
            self.save()
    def inc_fdl(self, fid):
        if fid in self.d["files"]:
            self.d["files"][fid]["downloads"] = self.d["files"][fid].get("downloads",0)+1
            self.save()
    def user_files(self, uid, page=0, pp=8):
        fs = [(k,v) for k,v in self.d["files"].items() if v["user_id"]==int(uid)]
        fs.sort(key=lambda x: x[1].get("upload_date",""), reverse=True)
        return fs[page*pp:(page+1)*pp], len(fs)
    def public_files(self, page=0, pp=8):
        fs = [(k,v) for k,v in self.d["files"].items() if v.get("is_public")]
        fs.sort(key=lambda x: x[1].get("upload_date",""), reverse=True)
        return fs[page*pp:(page+1)*pp], len(fs)
    def trending(self, limit=10):
        fs = [(k,v) for k,v in self.d["files"].items() if v.get("is_public")]
        fs.sort(key=lambda x: x[1].get("downloads",0), reverse=True)
        return fs[:limit]
    def search(self, q, uid=None, page=0, pp=8):
        q = q.lower()
        rs = []
        for fid, f in self.d["files"].items():
            if uid and f["user_id"] != int(uid): continue
            if not uid and not f.get("is_public"): continue
            if q in (f.get("file_name") or "").lower() or q in (f.get("caption") or "").lower():
                rs.append((fid, f))
        rs.sort(key=lambda x: x[1].get("downloads",0), reverse=True)
        return rs[page*pp:(page+1)*pp], len(rs)
    
    def file_count(self): return len(self.d["files"])
    def today_files(self):
        td = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        return sum(1 for f in self.d["files"].values() if f.get("upload_date","").startswith(td))
    def total_dl(self): return sum(f.get("downloads",0) for f in self.d["files"].values())
    def get_adel(self): return self.d["settings"].get("auto_delete_minutes", DEFAULT_AUTO_DELETE)
    def set_adel(self, m):
        self.d["settings"]["auto_delete_minutes"] = m
        self.save()
    def add_admin(self, uid):
        admins = self.d["settings"].setdefault("admins", [])
        if int(uid) not in admins:
            admins.append(int(uid))
            self.save()
    def rm_admin(self, uid):
        admins = self.d["settings"].setdefault("admins", [])
        if int(uid) in admins:
            admins.remove(int(uid))
            self.save()
    def backup_data(self): return {"signature":"FILEBRO_V3","bot":BOT_USERNAME,"date":now_iso(),"data":self.d}

db = DB(DB_FILE)

def is_admin(uid):
    return int(uid) in ADMIN_IDS or int(uid) in db.d["settings"].get("admins", [])

# ═══════════════════════════════════════════════════════════════
#  STATE
# ═══════════════════════════════════════════════════════════════

user_state: Dict[int, Dict[str, Any]] = {}
bc_store: Dict[int, Dict[str, Any]] = {}

def set_state(uid, action, **kw): user_state[uid] = {"action": action, **kw}
def get_state(uid): return user_state.get(uid, {})
def clear_state(uid): user_state.pop(uid, None)

# ═══════════════════════════════════════════════════════════════
#  TRANSLATIONS
# ═══════════════════════════════════════════════════════════════

LANG_FLAGS = {"en":"🇬🇧","bn":"🇧🇩","hi":"🇮🇳","ur":"🇵🇰","ru":"🇷🇺","ar":"🇸🇦"}
LANG_NAMES = {"en":"English","bn":"বাংলা","hi":"हिन्दी","ur":"اردو","ru":"Русский","ar":"العربية"}

T = {
"en": {
    "welcome_new": "ᯓᡣ𐭩 <b>Welcome to {bot}!</b>\n\nI can store your files and generate permanent shareable links.\n\n⌾ <b>Please select your language:</b>",
    "welcome_back": "╔════════════════════╗\n       {bt}\n╚════════════════════╝\n\n𖧧 Welcome back, <b>{name}</b>!\n\n𖦹 <b>{ss}:</b>\n𐙚 Files: <b>{fc}</b>  ·  ↧ Downloads: <b>{dl}</b>\n\n<i>Send me any file or use buttons below:</i>",
    "lang_set": "✧ Language set to <b>English</b>!\n\nSend me any file to get started.",
    "help": "╔════════════════════╗\n       ⍰ {t}\n╚════════════════════╝\n\n<b>How to use:</b>\n1️⃣ Send any file (photo, video, document, audio)\n2️⃣ Bot saves it and gives you a shareable link\n3️⃣ Share the link — anyone can download!\n\n<b>Features:</b>\n⊘ Password-protect links\n⌾ Public / Private visibility\n⌕ Search files\nᯓᡣ𐭩 Trending public files\n◷ Auto-delete from chat\n🌎 6 languages supported\n⚑ Advanced broadcast (Admin)\n𖡎 Ban/Unban users (Admin)\n\n<b>Support:</b> <a href='{ch}'>Channel</a>\n<b>Admin:</b> {ad}",
    "banned": "𖡎 <b>You have been banned from this bot.</b>",
    "err": "𖹭 An error occurred. Please try again.",
    "file_saved": "✧ <b>File Saved!</b>\n\n𖧷 Name: <code>{fn}</code>\n𖡼 Type: {ft}\n⊘ Visibility: {vis}\n⚿ Password: {pw}\n↧ Downloads: <b>{dl}</b>\n𖧹 Uploaded: {dt}",
    "not_found": "𖹭 <b>File not found</b> or link is invalid.",
    "adel_warn": "⟡ <b>Auto-Delete:</b> This file will be deleted in <b>{m} min</b>.\nSave it now or use the link below.",
    "expired": "◷ <b>File was auto-deleted.</b>\n\nClick below to get it again:",
    "enter_pw": "⚿ <b>This file is password-protected.</b>\n\nPlease enter the password:",
    "wrong_pw": "𖹭 <b>Wrong password.</b> Try again:",
    "must_join": "⚑ <b>You must join the channel to access this file:</b>\n\n⤑ {ch}\n\nAfter joining, click Verify below.",
    "ask_cap": "✐ <b>Send a caption</b> for this file, or click Skip:",
    "cap_ok": "✧ Caption updated!",
    "cap_skip": "✧ Saved without caption.",
    "pw_set": "✧ Password set: <code>{pw}</code>",
    "pw_rm": "✧ Password removed.",
    "ask_pw": "⚿ Send password to set (or 'remove' to clear):",
    "pub_on": "⌾ File is now <b>Public</b> — visible in trending & search.",
    "pub_off": "⊘ File is now <b>Private</b> — only via link.",
    "ask_fj": "⚑ Send channel username (e.g. @channel).\nBot must be admin there.\nSend 'remove' to clear.",
    "fj_set": "✧ Force-join set: {ch}",
    "fj_rm": "✧ Force-join removed.",
    "fj_ok": "✧ Verified! Getting your file...",
    "del_confirm": "⟡ <b>Delete this file?</b>\n\n𖧷 {fn}",
    "del_ok": "␡ File deleted.",
    "search_ask": "⌕ <b>Enter your search query:</b>",
    "search_res": "⌕ <b>Search Results</b> ({n} found):",
    "no_res": "😕 No results found.",
    "no_files": "📭 No files found.",
    "my_hdr": "𖹭 <b>Your Files</b> (Page {p}/{tp}):",
    "pub_hdr": "⟡ <b>Public Files</b> (Page {p}/{tp}):",
    "trend_hdr": "ᯓᡣ𐭩 <b>Trending Files</b> — Most Downloaded:",
    "ap": "╔════════════════════╗\n       ᯓᡣ𐭩 {t}\n╚════════════════════╝\n\n𖦹 Users: <b>{u}</b>  ·  𐙚 Files: <b>{f}</b>\n↧ Total Downloads: <b>{dl}</b>\n👤 Today Users: <b>{tu}</b>  ·  𖧷 Today Files: <b>{tf}</b>",
    "stats": "𖦹 <b>{t}</b>\n\n𖠋 Total Users: <b>{u}</b>\n𐙚 Total Files: <b>{f}</b>\n↧ Total Downloads: <b>{dl}</b>\n👤 New Today: <b>{tu}</b>\n𖧷 Files Today: <b>{tf}</b>",
    "bc_ask": "⚑ <b>Send the message to broadcast</b> (text, photo, video, etc.):",
    "bc_pre": "⚑ <b>Broadcast Preview</b>\n\nMessage stored. Choose an option:",
    "bc_go": "⚑ <b>Broadcasting to {n} users...</b>",
    "bc_done": "✧ <b>Broadcast Complete!</b>\n\n✓ Sent: <b>{ok}</b>\n⨂ Failed: <b>{fail}</b>",
    "bc_btn_ask": "⎔ Send button in format:\n<code>Button Text | https://url.com</code>",
    "bc_btn_ok": "✧ Button added: <b>{t}</b>",
    "bk_start": "⏳ Creating backup...",
    "bk_done": "✧ <b>Backup sent!</b>",
    "ban_ask": "𖡎 Send User ID to ban:",
    "unban_ask": "✧ Send User ID to unban:",
    "banned_ok": "𖡎 User <code>{uid}</code> banned.",
    "unbanned_ok": "✧ User <code>{uid}</code> unbanned.",
    "uinfo": "👤 <b>User Info</b>\n\nID: <code>{uid}</code>\nName: {nm}\nLang: {lg}\nFiles: {fc}\nDownloads: {dl}\nJoined: {dt}\nBanned: {bn}",
    "uid_ask": "👤 Send User ID:",
    "adel_ask": "◷ Send auto-delete time in minutes (current: {c}):",
    "set_ok": "✧ Auto-delete: <b>{m} min</b>",
    "set_panel": "𖣠 <b>{t}</b>\n\n◷ Auto-Delete: <b>{m} min</b>",
    "b_files":"𐙚 My Files","b_search":"⌕ Search","b_pub":"⌾ Public Files","b_trend":"🔥 Trending",
    "b_set":"𖣠 Settings","b_help":"⍰ Help","b_lang":"⌾ Language","b_back":"⟵ Back",
    "b_close":"⨂ Close","b_admin":"ᯓᡣ𐭩 Admin Panel","b_stats":"𖦹 Statistics","b_bc":"⚑ Broadcast",
    "b_users":"𖠋 Users","b_bk":"⎘ Backup","b_bset":"𖣠 Bot Settings","b_link":"⚲ Get Link",
    "b_pw":"⚿ Password","b_vis":"⊘ Visibility","b_cap":"✐ Caption","b_del":"␡ Delete",
    "b_fj":"⚑ Force Join","b_send":"⇪ Send Now","b_pin":"⌖ Send & Pin","b_addbtn":"⎔ Add Button",
    "b_cancel":"⊗ Cancel","b_ban":"𖡎 Ban User","b_unban":"✧ Unban","b_info":"𖭣 User Info",
    "b_yes":"✧ Yes, Delete","b_no":"⊗ No","b_next":"⟶","b_prev":"⟵",
    "b_dl":"⤓ Get File","b_ch":"⚑ Channel","b_contact":"𖠿 Admin","b_skip":"⇥ Skip",
    "b_verify":"✧ I Joined — Verify","b_mkpub":"⌾ Make Public","b_mkpriv":"⊘ Make Private",
},
"bn": {
    "welcome_new": "ᯓᡣ𐭩 <b>{bot}-এ স্বাগতম!</b>\n\nআমি আপনার ফাইল সংরক্ষণ করে স্থায়ী লিংক তৈরি করতে পারি।\n\n⌾ <b>আপনার ভাষা নির্বাচন করুন:</b>",
    "welcome_back": "╔════════════════════╗\n       {bt}\n╚════════════════════╝\n\n𖧧 স্বাগতম, <b>{name}</b>!\n\n𖦹 <b>{ss}:</b>\n𐙚 ফাইল: <b>{fc}</b>  ·  ↧ ডাউনলোড: <b>{dl}</b>\n\n<i>যেকোনো ফাইল পাঠান অথবা বাটন ব্যবহার করুন:</i>",
    "lang_set": "✧ ভাষা <b>বাংলা</b> সেট হয়েছে!\n\nশুরু করতে যেকোনো ফাইল পাঠান।",
    "help": "╔════════════════════╗\n       ⍰ {t}\n╚════════════════════╝\n\n<b>কিভাবে ব্যবহার করবেন:</b>\n1️⃣ যেকোনো ফাইল পাঠান\n2️⃣ বট সেভ করে লিংক দেবে\n3️⃣ লিংক শেয়ার করুন!\n\n<b>ফিচার:</b>\n⊘ পাসওয়ার্ড প্রটেকশন\n⌾ পাবলিক/প্রাইভেট\n⌕ সার্চ\nᯓᡣ𐭩 ট্রেন্ডিং\n◷ অটো-ডিলিট\n🌎 ৬টি ভাষা\n\n<b>সাপোর্ট:</b> <a href='{ch}'>চ্যানেল</a>\n<b>এডমিন:</b> {ad}",
    "banned": "𖡎 <b>আপনাকে বট থেকে নিষিদ্ধ করা হয়েছে।</b>",
    "err": "𖹭 ত্রুটি হয়েছে। আবার চেষ্টা করুন।",
    "file_saved": "✧ <b>ফাইল সেভ হয়েছে!</b>\n\n𖧷 নাম: <code>{fn}</code>\n𖡼 ধরন: {ft}\n⊘ দৃশ্যমানতা: {vis}\n⚿ পাসওয়ার্ড: {pw}\n↧ ডাউনলোড: <b>{dl}</b>\n𖧹 আপলোড: {dt}",
    "not_found": "𖹭 <b>ফাইল পাওয়া যায়নি।</b>",
    "adel_warn": "⟡ <b>অটো-ডিলিট:</b> ফাইলটি <b>{m} মিনিটে</b> মুছে যাবে।",
    "expired": "◷ <b>ফাইল অটো-ডিলিট হয়েছে।</b>\n\nআবার পেতে ক্লিক করুন:",
    "enter_pw": "⚿ <b>পাসওয়ার্ড সুরক্ষিত ফাইল।</b>\n\nপাসওয়ার্ড লিখুন:",
    "wrong_pw": "𖹭 <b>ভুল পাসওয়ার্ড।</b> আবার চেষ্টা করুন:",
    "must_join": "⚑ <b>ফাইল পেতে চ্যানেলে জয়েন করুন:</b>\n\n⤑ {ch}\n\nজয়েন করে Verify ক্লিক করুন।",
    "ask_cap": "✐ <b>ক্যাপশন পাঠান</b> অথবা Skip করুন:",
    "cap_ok": "✧ ক্যাপশন আপডেট!",
    "cap_skip": "✧ ক্যাপশন ছাড়া সেভ।",
    "pw_set": "✧ পাসওয়ার্ড: <code>{pw}</code>",
    "pw_rm": "✧ পাসওয়ার্ড সরানো হয়েছে।",
    "ask_pw": "⚿ পাসওয়ার্ড পাঠান ('remove' দিলে মুছবে):",
    "pub_on": "⌾ ফাইল এখন <b>পাবলিক</b>।",
    "pub_off": "⊘ ফাইল এখন <b>প্রাইভেট</b>।",
    "ask_fj": "⚑ চ্যানেল ইউজারনেম পাঠান (যেমন @channel)।\n'remove' দিলে মুছবে।",
    "fj_set": "✧ ফোর্স-জয়েন: {ch}",
    "fj_rm": "✧ ফোর্স-জয়েন সরানো হয়েছে।",
    "fj_ok": "✧ যাচাই সম্পন্ন!",
    "del_confirm": "⟡ <b>ফাইল মুছবেন?</b>\n\n𖧷 {fn}",
    "del_ok": "␡ ফাইল মুছে ফেলা হয়েছে।",
    "search_ask": "⌕ <b>সার্চ কোয়েরি লিখুন:</b>",
    "search_res": "⌕ <b>ফলাফল</b> ({n}টি পাওয়া গেছে):",
    "no_res": "😕 কিছু পাওয়া যায়নি।",
    "no_files": "📭 কোনো ফাইল নেই।",
    "my_hdr": "𖹭 <b>আপনার ফাইল</b> (পৃষ্ঠা {p}/{tp}):",
    "pub_hdr": "⟡ <b>পাবলিক ফাইল</b> (পৃষ্ঠা {p}/{tp}):",
    "trend_hdr": "ᯓᡣ𐭩 <b>ট্রেন্ডিং ফাইল</b>:",
    "ap": "╔════════════════════╗\n       ᯓᡣ𐭩 {t}\n╚════════════════════╝\n\n𖦹 ইউজার: <b>{u}</b>  ·  𐙚 ফাইল: <b>{f}</b>\n↧ ডাউনলোড: <b>{dl}</b>\n👤 আজ: <b>{tu}</b>  ·  𖧷 আজ ফাইল: <b>{tf}</b>",
    "stats": "𖦹 <b>{t}</b>\n\n𖠋 ইউজার: <b>{u}</b>\n𐙚 ফাইল: <b>{f}</b>\n↧ ডাউনলোড: <b>{dl}</b>\n👤 আজ নতুন: <b>{tu}</b>\n𖧷 আজ ফাইল: <b>{tf}</b>",
    "bc_ask": "⚑ <b>ব্রডকাস্ট মেসেজ পাঠান:</b>",
    "bc_pre": "⚑ <b>প্রিভিউ</b>\n\nমেসেজ সেভ। অপশন বেছে নিন:",
    "bc_go": "⚑ <b>{n} জনকে পাঠানো হচ্ছে...</b>",
    "bc_done": "✧ <b>সম্পন্ন!</b>\n\n✓ সফল: <b>{ok}</b>\n⨂ ব্যর্থ: <b>{fail}</b>",
    "bc_btn_ask": "⎔ বাটন:\n<code>টেক্সট | URL</code>",
    "bc_btn_ok": "✧ বাটন যোগ: <b>{t}</b>",
    "bk_start": "⏳ ব্যাকআপ তৈরি হচ্ছে...",
    "bk_done": "✧ <b>ব্যাকআপ পাঠানো হয়েছে!</b>",
    "ban_ask": "𖡎 ব্যান করতে User ID:",
    "unban_ask": "✧ আনব্যান করতে User ID:",
    "banned_ok": "𖡎 <code>{uid}</code> ব্যান।",
    "unbanned_ok": "✧ <code>{uid}</code> আনব্যান।",
    "uinfo": "👤 <b>তথ্য</b>\n\nID: <code>{uid}</code>\nনাম: {nm}\nভাষা: {lg}\nফাইল: {fc}\nডাউনলোড: {dl}\nযোগদান: {dt}\nব্যান: {bn}",
    "uid_ask": "👤 User ID পাঠান:",
    "adel_ask": "◷ অটো-ডিলিট মিনিট (বর্তমান: {c}):",
    "set_ok": "✧ অটো-ডিলিট: <b>{m} মিনিট</b>",
    "set_panel": "𖣠 <b>{t}</b>\n\n◷ অটো-ডিলিট: <b>{m} মিনিট</b>",
    "b_files":"𐙚 আমার ফাইল","b_search":"⌕ সার্চ","b_pub":"⌾ পাবলিক","b_trend":"🔥 ট্রেন্ডিং",
    "b_set":"𖣠 সেটিংস","b_help":"⍰ সাহায্য","b_lang":"⌾ ভাষা","b_back":"⟵ পিছনে",
    "b_close":"⨂ বন্ধ","b_admin":"ᯓᡣ𐭩 এডমিন","b_stats":"𖦹 পরিসংখ্যান","b_bc":"⚑ ব্রডকাস্ট",
    "b_users":"𖠋 ইউজার","b_bk":"⎘ ব্যাকআপ","b_bset":"𖣠 বট সেটিংস","b_link":"⚲ লিংক",
    "b_pw":"⚿ পাসওয়ার্ড","b_vis":"⊘ দৃশ্যমানতা","b_cap":"✐ ক্যাপশন","b_del":"␡ মুছুন",
    "b_fj":"⚑ ফোর্স জয়েন","b_send":"⇪ পাঠান","b_pin":"⌖ পাঠান+পিন","b_addbtn":"⎔ বাটন",
    "b_cancel":"⊗ বাতিল","b_ban":"𖡎 ব্যান","b_unban":"✧ আনব্যান","b_info":"𖭣 তথ্য",
    "b_yes":"✧ হ্যাঁ","b_no":"⊗ না","b_next":"⟶","b_prev":"⟵",
    "b_dl":"⤓ ফাইল নিন","b_ch":"⚑ চ্যানেল","b_contact":"𖠿 এডমিন","b_skip":"⇥ স্কিপ",
    "b_verify":"✧ জয়েন করেছি","b_mkpub":"⌾ পাবলিক","b_mkpriv":"⊘ প্রাইভেট",
},
"hi": {
    "welcome_new": "ᯓᡣ𐭩 <b>{bot} में स्वागत है!</b>\n\nमैं आपकी फ़ाइलें सहेज कर स्थायी लिंक बना सकता हूँ।\n\n⌾ <b>अपनी भाषा चुनें:</b>",
    "welcome_back": "╔════════════════════╗\n       {bt}\n╚════════════════════╝\n\n𖧧 वापसी पर स्वागत, <b>{name}</b>!\n\n𖦹 <b>{ss}:</b>\n𐙚 फ़ाइलें: <b>{fc}</b>  ·  ↧ डाउनलोड: <b>{dl}</b>\n\n<i>कोई भी फ़ाइल भेजें या बटन दबाएँ:</i>",
    "lang_set": "✧ भाषा <b>हिन्दी</b> सेट की गई!\n\nशुरू करने के लिए कोई फ़ाइल भेजें।",
    "help": "╔════════════════════╗\n       ⍰ {t}\n╚════════════════════╝\n\n<b>कैसे उपयोग करें:</b>\n1️⃣ कोई भी फ़ाइल भेजें\n2️⃣ बॉट सेव करके लिंक देगा\n3️⃣ लिंक शेयर करें!\n\n<b>फ़ीचर:</b>\n⊘ पासवर्ड सुरक्षा\n⌾ सार्वजनिक/निजी\n⌕ खोज\nᯓᡣ𐭩 ट्रेंडिंग\n◷ ऑटो-डिलीट\n🌎 6 भाषाएँ\n\n<b>सहायता:</b> <a href='{ch}'>चैनल</a>\n<b>एडमिन:</b> {ad}",
    "banned": "𖡎 <b>आपको इस बॉट से प्रतिबंधित किया गया है।</b>",
    "err": "𖹭 एक त्रुटि हुई। कृपया पुनः प्रयास करें।",
    "file_saved": "✧ <b>फ़ाइल सेव हो गई!</b>\n\n𖧷 नाम: <code>{fn}</code>\n𖡼 प्रकार: {ft}\n⊘ दृश्यता: {vis}\n⚿ पासवर्ड: {pw}\n↧ डाउनलोड: <b>{dl}</b>\n𖧹 अपलोड: {dt}",
    "not_found": "𖹭 <b>फ़ाइल नहीं मिली।</b>",
    "adel_warn": "⟡ <b>ऑटो-डिलीट:</b> यह फ़ाइल <b>{m} मिनट</b> में हट जाएगी।",
    "expired": "◷ <b>फ़ाइल ऑटो-डिलीट हो गई।</b>\n\nदोबारा पाने के लिए क्लिक करें:",
    "enter_pw": "⚿ <b>यह फ़ाइल पासवर्ड-सुरक्षित है।</b>\n\nपासवर्ड दर्ज करें:",
    "wrong_pw": "𖹭 <b>गलत पासवर्ड।</b> पुनः प्रयास करें:",
    "must_join": "⚑ <b>फ़ाइल पाने के लिए चैनल ज्वाइन करें:</b>\n\n⤑ {ch}\n\nज्वाइन करने के बाद Verify पर क्लिक करें।",
    "ask_cap": "✐ <b>कैप्शन भेजें</b> या Skip दबाएँ:",
    "cap_ok": "✧ कैप्शन अपडेट हो गया!",
    "cap_skip": "✧ बिना कैप्शन सेव किया गया।",
    "pw_set": "✧ पासवर्ड सेट: <code>{pw}</code>",
    "pw_rm": "✧ पासवर्ड हटाया गया।",
    "ask_pw": "⚿ पासवर्ड भेजें ('remove' से हटाएँ):",
    "pub_on": "⌾ फ़ाइल अब <b>सार्वजनिक</b> है।",
    "pub_off": "⊘ फ़ाइल अब <b>निजी</b> है।",
    "ask_fj": "⚑ चैनल यूजरनेम भेजें (जैसे @channel)।\n'remove' से हटाएँ।",
    "fj_set": "✧ फोर्स-ज्वाइन सेट: {ch}",
    "fj_rm": "✧ फोर्स-ज्वाइन हटाया गया।",
    "fj_ok": "✧ सत्यापित!",
    "del_confirm": "⟡ <b>क्या आप फ़ाइल हटाना चाहते हैं?</b>\n\n𖧷 {fn}",
    "del_ok": "␡ फ़ाइल हटा दी गई।",
    "search_ask": "⌕ <b>खोज शब्द लिखें:</b>",
    "search_res": "⌕ <b>खोज परिणाम</b> ({n} मिले):",
    "no_res": "😕 कुछ नहीं मिला।",
    "no_files": "📭 कोई फ़ाइल नहीं।",
    "my_hdr": "𖹭 <b>आपकी फ़ाइलें</b> (पृष्ठ {p}/{tp}):",
    "pub_hdr": "⟡ <b>सार्वजनिक फ़ाइलें</b> (पृष्ठ {p}/{tp}):",
    "trend_hdr": "ᯓᡣ𐭩 <b>ट्रेंडिंग फ़ाइलें</b>:",
    "ap": "╔════════════════════╗\n       ᯓᡣ𐭩 {t}\n╚════════════════════╝\n\n𖦹 उपयोगकर्ता: <b>{u}</b>  ·  𐙚 फ़ाइलें: <b>{f}</b>\n↧ डाउनलोड: <b>{dl}</b>\n👤 आज के उपयोगकर्ता: <b>{tu}</b>  ·  𖧷 आज की फ़ाइलें: <b>{tf}</b>",
    "stats": "𖦹 <b>{t}</b>\n\n𖠋 कुल उपयोगकर्ता: <b>{u}</b>\n𐙚 कुल फ़ाइलें: <b>{f}</b>\n↧ कुल डाउनलोड: <b>{dl}</b>\n👤 आज नए: <b>{tu}</b>\n𖧷 आज की फ़ाइलें: <b>{tf}</b>",
    "bc_ask": "⚑ <b>ब्रॉडकास्ट मैसेज भेजें:</b>",
    "bc_pre": "⚑ <b>प्रीव्यू</b>\n\nमैसेज सेव हो गया। विकल्प चुनें:",
    "bc_go": "⚑ <b>{n} लोगों को भेजा जा रहा है...</b>",
    "bc_done": "✧ <b>पूर्ण!</b>\n\n✓ सफल: <b>{ok}</b>\n⨂ असफल: <b>{fail}</b>",
    "bc_btn_ask": "⎔ बटन:\n<code>टेक्स्ट | URL</code>",
    "bc_btn_ok": "✧ बटन जोड़ा गया: <b>{t}</b>",
    "bk_start": "⏳ बैकअप बनाया जा रहा है...",
    "bk_done": "✧ <b>बैकআপ भेजा गया!</b>",
    "ban_ask": "𖡎 बैन के लिए User ID भेजें:",
    "unban_ask": "✧ अनबैन के लिए User ID भेजें:",
    "banned_ok": "𖡎 <code>{uid}</code> बैन किया गया।",
    "unbanned_ok": "✧ <code>{uid}</code> अनबैन किया गया।",
    "uinfo": "👤 <b>जानकारी</b>\n\nID: <code>{uid}</code>\nनाम: {nm}\nभाषा: {lg}\nफ़ाइलें: {fc}\nडाउनलोड: {dl}\nशामिल: {dt}\nबैन: {bn}",
    "uid_ask": "👤 User ID भेजें:",
    "adel_ask": "◷ ऑटो-डिलीट समय मिनटों में (वर्तमान: {c}):",
    "set_ok": "✧ ऑटो-डिलीट: <b>{m} मिनट</b>",
    "set_panel": "𖣠 <b>{t}</b>\n\n◷ ऑटो-डिलीट: <b>{m} मिनट</b>",
    "b_files":"𐙚 मेरी फ़ाइलें","b_search":"⌕ खोजें","b_pub":"⌾ सार्वजनिक","b_trend":"🔥 ट्रेंडिंग",
    "b_set":"𖣠 सेटिंग्स","b_help":"⍰ मदद","b_lang":"⌾ भाषा","b_back":"⟵ वापस",
    "b_close":"⨂ बंद","b_admin":"ᯓᡣ𐭩 एडमिन","b_stats":"𖦹 आँकड़े","b_bc":"⚑ ब्रॉडकास्ट",
    "b_users":"𖠋 उपयोगकर्ता","b_bk":"⎘ बैकअप","b_bset":"𖣠 बॉट सेटिंग्स","b_link":"⚲ लिंक",
    "b_pw":"⚿ पासवर्ड","b_vis":"⊘ दृश्यता","b_cap":"✐ कैप्शन","b_del":"␡ हटाएँ",
    "b_fj":"⚑ फोर्स ज्वाइन","b_send":"⇪ भेजें","b_pin":"⌖ भेजें+पिन","b_addbtn":"⎔ बटन",
    "b_cancel":"⊗ रद्द","b_ban":"𖡎 बैन","b_unban":"✧ अनबैन","b_info":"𖭣 जानकारी",
    "b_yes":"✧ हाँ","b_no":"⊗ नहीं","b_next":"⟶","b_prev":"⟵",
    "b_dl":"⤓ फ़ाइल लें","b_ch":"⚑ चैनल","b_contact":"𖠿 एडमिन","b_skip":"⇥ स्किप",
    "b_verify":"✧ सत्यापित","b_mkpub":"⌾ सार्वजनिक","b_mkpriv":"⊘ निजी",
},
"ur": {
    "welcome_new": "ᯓᡣ𐭩 <b>{bot} میں خوش آمدید!</b>\n\nمیں فائلیں محفوظ کر کے مستقل لنک بناتا ہوں۔\n\n⌾ <b>زبان منتخب کریں:</b>",
    "welcome_back": "╔════════════════════╗\n       {bt}\n╚════════════════════╝\n\n𖧧 واپسی پر خوش آمدید، <b>{name}</b>!\n\n𖦹 <b>{ss}:</b>\n𐙚 فائلیں: <b>{fc}</b>  ·  ↧ ڈاؤن لوڈ: <b>{dl}</b>\n\n<i>کوئی بھی فائل بھیجیں:</i>",
    "lang_set": "✧ زبان <b>اردو</b> سیٹ ہو گئی!\n\nشروع کرنے کے لیے کوئی فائل بھیجیں۔",
    "help": "╔════════════════════╗\n       ⍰ {t}\n╚════════════════════╝\n\n<b>طریقہ:</b>\n1️⃣ فائل بھیجیں\n2️⃣ بوٹ لنک دے گا\n3️⃣ شیئر کریں!\n\n<b>خصوصیات:</b>\n⊘ پاسورڈ\n⌾ عوامی/نجی\n⌕ تلاش\nᯓᡣ𐭩 ٹرینڈنگ\n◷ آٹو ڈیلیٹ\n🌎 6 زبانیں\n\n<b>مدد:</b> <a href='{ch}'>چینل</a>\n<b>ایڈمن:</b> {ad}",
    "banned": "𖡎 <b>آپ پر پابندی ہے۔</b>",
    "err": "𖹭 ایک خرابی ہوئی۔",
    "file_saved": "✧ <b>فائل محفوظ!</b>\n\n𖧷 نام: <code>{fn}</code>\n𖡼 قسم: {ft}\n⊘ مرئیت: {vis}\n⚿ پاسورڈ: {pw}\n↧ ڈاؤن لوڈ: <b>{dl}</b>\n𖧹 اپ لوڈ: {dt}",
    "not_found": "𖹭 <b>فائل نہیں ملی۔</b>",
    "adel_warn": "⟡ <b>آٹو ڈیلیٹ:</b> فائل <b>{m} منٹ</b> میں حذف ہو گی۔",
    "expired": "◷ <b>حذف ہو گئی۔</b>\n\nدوبارہ حاصل کرنے کے لیے کلک کریں:",
    "enter_pw": "⚿ <b>یہ پاسورڈ سے محفوظ ہے۔</b>\n\nپاسورڈ درج کریں:",
    "wrong_pw": "𖹭 <b>غلط پاسورڈ۔</b>",
    "must_join": "⚑ <b>فائل کے لیے چینل جوائن کریں:</b>\n\n⤑ {ch}\n\nپھر Verify پر کلک کریں۔",
    "ask_cap": "✐ <b>کیپشن بھیجیں</b> یا Skip دبائیں:",
    "cap_ok": "✧ کیپشن اپ ڈیٹ!",
    "cap_skip": "✧ بغیر کیپشن محفوظ۔",
    "pw_set": "✧ پاسورڈ سیٹ: <code>{pw}</code>",
    "pw_rm": "✧ پاسورڈ ہٹایا گیا۔",
    "ask_pw": "⚿ پاسورڈ بھیجیں ('remove' سے ہٹائیں):",
    "pub_on": "⌾ فائل اب <b>عوامی</b> ہے۔",
    "pub_off": "⊘ فائل اب <b>نجی</b> ہے۔",
    "ask_fj": "⚑ چینل یوزرنیم (جیسے @channel)۔\n'remove' سے ہٹائیں۔",
    "fj_set": "✧ فورس جوائن: {ch}",
    "fj_rm": "✧ فورس جوائن ہٹایا گیا۔",
    "fj_ok": "✧ تصدیق مکمل!",
    "del_confirm": "⟡ <b>فائل حذف کریں?</b>\n\n𖧷 {fn}",
    "del_ok": "␡ حذف کی گئی۔",
    "search_ask": "⌕ <b>تلاش کریں:</b>",
    "search_res": "⌕ <b>نتائج</b> ({n} ملے):",
    "no_res": "😕 کچھ نہیں ملا۔",
    "no_files": "📭 کوئی فائل نہیں۔",
    "my_hdr": "𖹭 <b>آپ کی فائلیں</b> (صفحہ {p}/{tp}):",
    "pub_hdr": "⟡ <b>عوامی فائلیں</b> (صفحہ {p}/{tp}):",
    "trend_hdr": "ᯓᡣ𐭩 <b>ٹرینڈنگ فائلیں</b>:",
    "ap": "╔════════════════════╗\n       ᯓᡣ𐭩 {t}\n╚════════════════════╝\n\n𖦹 صارفین: <b>{u}</b>  ·  𐙚 فائلیں: <b>{f}</b>\n↧ ڈاؤن لوڈ: <b>{dl}</b>\n👤 آج: <b>{tu}</b>  ·  𖧷 آج کی فائلیں: <b>{tf}</b>",
    "stats": "𖦹 <b>{t}</b>\n\n𖠋 صارفین: <b>{u}</b>\n𐙚 فائلیں: <b>{f}</b>\n↧ ڈاؤن لوڈ: <b>{dl}</b>\n👤 آج نئے: <b>{tu}</b>\n𖧷 آج کی فائلیں: <b>{tf}</b>",
    "bc_ask": "⚑ <b>براڈکاسٹ میسج بھیجیں:</b>",
    "bc_pre": "⚑ <b>پریویو</b>\n\nمحفوظ۔ آپشن چنیں:",
    "bc_go": "⚑ <b>{n} کو بھیجا جا رہا ہے...</b>",
    "bc_done": "✧ <b>مکمل!</b>\n\n✓ کامیاب: <b>{ok}</b>\n⨂ ناکام: <b>{fail}</b>",
    "bc_btn_ask": "⎔ بٹن:\n<code>ٹیکسٹ | URL</code>",
    "bc_btn_ok": "✧ بٹن شامل: <b>{t}</b>",
    "bk_start": "⏳ بیک اپ بن رہا ہے...",
    "bk_done": "✧ <b>بیک اپ بھیجا گیا!</b>",
    "ban_ask": "𖡎 بین کے لیے ID:",
    "unban_ask": "✧ ان بین کے لیے ID:",
    "banned_ok": "𖡎 <code>{uid}</code> بین۔",
    "unbanned_ok": "✧ <code>{uid}</code> ان بین۔",
    "uinfo": "👤 <b>معلومات</b>\n\nID: <code>{uid}</code>\nنام: {nm}\nزبان: {lg}\nفائلیں: {fc}\nڈاؤن لوڈ: {dl}\nشمولیت: {dt}\nبین: {bn}",
    "uid_ask": "👤 User ID:",
    "adel_ask": "◷ آٹو ڈیلیٹ منٹ ({c}):",
    "set_ok": "✧ آٹو ڈیلیٹ: <b>{m} منٹ</b>",
    "set_panel": "𖣠 <b>{t}</b>\n\n◷ آٹو ڈیلیٹ: <b>{m} منٹ</b>",
    "b_files":"𐙚 میری فائلیں","b_search":"⌕ تلاش","b_pub":"⌾ عوامی","b_trend":"🔥 ٹرینڈنگ",
    "b_set":"𖣠 ترتیبات","b_help":"⍰ مدد","b_lang":"⌾ زبان","b_back":"⟵ واپس",
    "b_close":"⨂ بند","b_admin":"ᯓᡣ𐭩 ایڈمن","b_stats":"𖦹 اعداد","b_bc":"⚑ براڈکاسٹ",
    "b_users":"𖠋 صارفین","b_bk":"⎘ بیک اپ","b_bset":"𖣠 سیٹنگز","b_link":"⚲ لنک",
    "b_pw":"⚿ پاسورڈ","b_vis":"⊘ مرئیت","b_cap":"✐ کیپشن","b_del":"␡ حذف",
    "b_fj":"⚑ فورس جوائن","b_send":"⇪ بھیجیں","b_pin":"⌖ بھیجیں+پن","b_addbtn":"⎔ بٹن",
    "b_cancel":"⊗ منسوخ","b_ban":"𖡎 بین","b_unban":"✧ ان بین","b_info":"𖭣 معلومات",
    "b_yes":"✧ ہاں","b_no":"⊗ نہیں","b_next":"⟶","b_prev":"⟵",
    "b_dl":"⤓ حاصل کریں","b_ch":"⚑ چینل","b_contact":"𖠿 ایڈمن","b_skip":"⇥ چھوڑیں",
    "b_verify":"✧ تصدیق","b_mkpub":"⌾ عوامی","b_mkpriv":"⊘ نجی",
},
"ru": {
    "welcome_new": "ᯓᡣ𐭩 <b>Добро пожаловать в {bot}!</b>\n\nЯ храню ваши файлы и создаю ссылки.\n\n⌾ <b>Выберите язык:</b>",
    "welcome_back": "╔════════════════════╗\n       {bt}\n╚════════════════════╝\n\n𖧧 С возвращением, <b>{name}</b>!\n\n𖦹 <b>{ss}:</b>\n𐙚 Файлов: <b>{fc}</b>  ·  ↧ Загрузок: <b>{dl}</b>\n\n<i>Отправьте файл или нажмите кнопки:</i>",
    "lang_set": "✧ Язык установлен: <b>Русский</b>!\n\nОтправьте файл.",
    "help": "╔════════════════════╗\n       ⍰ {t}\n╚════════════════════╝\n\n<b>Как пользоваться:</b>\n1️⃣ Отправьте файл\n2️⃣ Бот даст ссылку\n3️⃣ Поделитесь!\n\n<b>Функции:</b>\n⊘ Пароль\n⌾ Публ/Прив\n⌕ Поиск\nᯓᡣ𐭩 Тренды\n◷ Автоудаление\n🌎 6 языков\n\n<b>Поддержка:</b> <a href='{ch}'>Канал</a>\n<b>Админ:</b> {ad}",
    "banned": "𖡎 <b>Вы заблокированы.</b>",
    "err": "𖹭 Ошибка. Попробуйте еще раз.",
    "file_saved": "✧ <b>Файл сохранён!</b>\n\n𖧷 Имя: <code>{fn}</code>\n𖡼 Тип: {ft}\n⊘ Видимость: {vis}\n⚿ Пароль: {pw}\n↧ Загрузок: <b>{dl}</b>\n𖧹 Загружен: {dt}",
    "not_found": "𖹭 <b>Файл не найден.</b>",
    "adel_warn": "⟡ <b>Автоудаление:</b> файл удалится через <b>{m} мин</b>.",
    "expired": "◷ <b>Файл автоудалeн.</b>\n\nНажмите ниже:",
    "enter_pw": "⚿ <b>Защищено паролем.</b>\n\nВведите пароль:",
    "wrong_pw": "𖹭 <b>Неверный пароль.</b>",
    "must_join": "⚑ <b>Вступите в канал:</b>\n\n⤑ {ch}\n\nЗатем нажмите Проверить.",
    "ask_cap": "✐ <b>Отправьте подпись</b> или нажмите Пропустить:",
    "cap_ok": "✧ Подпись обновлена!",
    "cap_skip": "✧ Сохранено без подписи.",
    "pw_set": "✧ Пароль: <code>{pw}</code>",
    "pw_rm": "✧ Пароль удалён.",
    "ask_pw": "⚿ Отправьте пароль ('remove' для удаления):",
    "pub_on": "⌾ Файл теперь <b>Публичный</b>.",
    "pub_off": "⊘ Файл теперь <b>Приватный</b>.",
    "ask_fj": "⚑ Юзернейм канала (например @channel).\n'remove' для удаления.",
    "fj_set": "✧ Подписка: {ch}",
    "fj_rm": "✧ Подписка удалена.",
    "fj_ok": "✧ Проверено!",
    "del_confirm": "⟡ <b>Удалить файл?</b>\n\n𖧷 {fn}",
    "del_ok": "␡ Файл удалён.",
    "search_ask": "⌕ <b>Поиск:</b>",
    "search_res": "⌕ <b>Результаты</b> (найдено {n}):",
    "no_res": "😕 Ничего не найдено.",
    "no_files": "📭 Нет файлов.",
    "my_hdr": "𖹭 <b>Ваши файлы</b> (стр. {p}/{tp}):",
    "pub_hdr": "⟡ <b>Публичные файлы</b> (стр. {p}/{tp}):",
    "trend_hdr": "ᯓᡣ𐭩 <b>Трендовые файлы</b>:",
    "ap": "╔════════════════════╗\n       ᯓᡣ𐭩 {t}\n╚════════════════════╝\n\n𖦹 Польз-лей: <b>{u}</b>  ·  𐙚 Файлов: <b>{f}</b>\n↧ Загрузок: <b>{dl}</b>\n👤 Сегодня: <b>{tu}</b>  ·  𖧷 Сегодня файлов: <b>{tf}</b>",
    "stats": "𖦹 <b>{t}</b>\n\n𖠋 Всего польз.: <b>{u}</b>\n𐙚 Всего файлов: <b>{f}</b>\n↧ Всего загрузок: <b>{dl}</b>\n👤 Новых сегодня: <b>{tu}</b>\n𖧷 Файлов сегодня: <b>{tf}</b>",
    "bc_ask": "⚑ <b>Сообщение для рассылки:</b>",
    "bc_pre": "⚑ <b>Предпросмотр</b>\n\nСохранено. Выберите:",
    "bc_go": "⚑ <b>Рассылка {n} пользователям...</b>",
    "bc_done": "✧ <b>Готово!</b>\n\n✓ Успешно: <b>{ok}</b>\n⨂ Ошибка: <b>{fail}</b>",
    "bc_btn_ask": "⎔ Кнопка:\n<code>Текст | URL</code>",
    "bc_btn_ok": "✧ Кнопка: <b>{t}</b>",
    "bk_start": "⏳ Создание бэкапа...",
    "bk_done": "✧ <b>Бэкап отправлен!</b>",
    "ban_ask": "𖡎 User ID для бана:",
    "unban_ask": "✧ User ID для разбана:",
    "banned_ok": "𖡎 <code>{uid}</code> забанен.",
    "unbanned_ok": "✧ <code>{uid}</code> разбанен.",
    "uinfo": "👤 <b>Инфо</b>\n\nID: <code>{uid}</code>\nИмя: {nm}\nЯзык: {lg}\nФайлов: {fc}\nЗагрузок: {dl}\nДата: {dt}\nБан: {bn}",
    "uid_ask": "👤 Отправьте User ID:",
    "adel_ask": "◷ Минуты автоудаления ({c}):",
    "set_ok": "✧ Автоудаление: <b>{m} мин</b>",
    "set_panel": "𖣠 <b>{t}</b>\n\n◷ Автоудаление: <b>{m} мин</b>",
    "b_files":"𐙚 Мои файлы","b_search":"⌕ Поиск","b_pub":"⌾ Публичные","b_trend":"🔥 Тренды",
    "b_set":"𖣠 Настройки","b_help":"⍰ Помощь","b_lang":"⌾ Язык","b_back":"⟵ Назад",
    "b_close":"⨂ Закрыть","b_admin":"ᯓᡣ𐭩 Админ","b_stats":"𖦹 Статистика","b_bc":"⚑ Рассылка",
    "b_users":"𖠋 Пользователи","b_bk":"⎘ Бэкап","b_bset":"𖣠 Настройки бота","b_link":"⚲ Ссылка",
    "b_pw":"⚿ Пароль","b_vis":"⊘ Видимость","b_cap":"✐ Подпись","b_del":"␡ Удалить",
    "b_fj":"⚑ Подписка","b_send":"⇪ Отправить","b_pin":"⌖ Отпр+Закреп","b_addbtn":"⎔ Кнопка",
    "b_cancel":"⊗ Отмена","b_ban":"𖡎 Бан","b_unban":"✧ Разбан","b_info":"𖭣 Инфо",
    "b_yes":"✧ Да","b_no":"⊗ Нет","b_next":"⟶","b_prev":"⟵",
    "b_dl":"⤓ Скачать","b_ch":"⚑ Канал","b_contact":"𖠿 Админ","b_skip":"⇥ Пропуск",
    "b_verify":"✧ Проверить","b_mkpub":"⌾ Публичным","b_mkpriv":"⊘ Приватным",
},
"ar": {
    "welcome_new": "ᯓᡣ𐭩 <b>مرحباً في {bot}!</b>\n\nأحفظ ملفاتك وأنشئ روابط دائمة.\n\n⌾ <b>اختر لغتك:</b>",
    "welcome_back": "╔════════════════════╗\n       {bt}\n╚════════════════════╝\n\n𖧧 أهلاً، <b>{name}</b>!\n\n𖦹 <b>{ss}:</b>\n𐙚 ملفات: <b>{fc}</b>  ·  ↧ تنزيلات: <b>{dl}</b>\n\n<i>أرسل أي ملف:</i>",
    "lang_set": "✧ اللغة: <b>العربية</b>!\n\nأرسل ملف للبدء.",
    "help": "╔════════════════════╗\n       ⍰ {t}\n╚════════════════════╝\n\n<b>الطريقة:</b>\n1️⃣ أرسل ملف\n2️⃣ احصل على رابط\n3️⃣ شارك!\n\n<b>الميزات:</b>\n⊘ كلمة مرور\n⌾ عام/خاص\n⌕ بحث\nᯓᡣ𐭩 رائج\n◷ حذف تلقائي\n🌎 6 لغات\n\n<b>الدعم:</b> <a href='{ch}'>القناة</a>\n<b>المشرف:</b> {ad}",
    "banned": "𖡎 <b>أنت محظور.</b>",
    "err": "𖹭 حدث خطأ.",
    "file_saved": "✧ <b>تم الحفظ!</b>\n\n𖧷 الاسم: <code>{fn}</code>\n𖡼 النوع: {ft}\n⊘ الرؤية: {vis}\n⚿ كلمة المرور: {pw}\n↧ التنزيلات: <b>{dl}</b>\n𖧹 الرفع: {dt}",
    "not_found": "𖹭 <b>الملف غير موجود.</b>",
    "adel_warn": "⟡ <b>حذف تلقائي:</b> سيُحذف بعد <b>{m} دقيقة</b>.",
    "expired": "◷ <b>تم الحذف التلقائي.</b>\n\nاضغط هنا:",
    "enter_pw": "⚿ <b>محمي بكلمة مرور.</b>\n\nأدخل كلمة المرور:",
    "wrong_pw": "𖹭 <b>خاطئة.</b>",
    "must_join": "⚑ <b>انضم للقناة:</b>\n\n⤑ {ch}\n\nثم اضغط تحقق.",
    "ask_cap": "✐ <b>أرسل عنواناً</b> أو تخطي:",
    "cap_ok": "✧ تم التحديث!",
    "cap_skip": "✧ حفظ بدون عنوان.",
    "pw_set": "✧ كلمة المرور: <code>{pw}</code>",
    "pw_rm": "✧ أُزيلت كلمة المرور.",
    "ask_pw": "⚿ أرسل كلمة المرور ('remove' للإزالة):",
    "pub_on": "⌾ الملف <b>عام</b>.",
    "pub_off": "⊘ الملف <b>خاص</b>.",
    "ask_fj": "⚑ يوزر القناة (@channel).\n'remove' للإزالة.",
    "fj_set": "✧ انضمام إجباري: {ch}",
    "fj_rm": "✧ أُزيل الانضمام الإجباري.",
    "fj_ok": "✧ تم التحقق!",
    "del_confirm": "⟡ <b>حذف هذا الملف?</b>\n\n𖧷 {fn}",
    "del_ok": "␡ تم الحذف.",
    "search_ask": "⌕ <b>أدخل كلمة البحث:</b>",
    "search_res": "⌕ <b>النتائج</b> ({n}):",
    "no_res": "😕 لا توجد نتائج.",
    "no_files": "📭 لا ملفات.",
    "my_hdr": "𖹭 <b>ملفاتك</b> (صفحة {p}/{tp}):",
    "pub_hdr": "⟡ <b>الملفات العامة</b> (صفحة {p}/{tp}):",
    "trend_hdr": "ᯓᡣ𐭩 <b>الملفات الرائجة</b>:",
    "ap": "╔════════════════════╗\n       ᯓᡣ𐭩 {t}\n╚════════════════════╝\n\n𖦹 المستخدمون: <b>{u}</b>  ·  𐙚 الملفات: <b>{f}</b>\n↧ التنزيلات: <b>{dl}</b>\n👤 مستخدمو اليوم: <b>{tu}</b>  ·  𖧷 ملفات اليوم: <b>{tf}</b>",
    "stats": "𖦹 <b>{t}</b>\n\n𖠋 إجمالي المستخدمين: <b>{u}</b>\n𐙚 إجمالي الملفات: <b>{f}</b>\n↧ إجمالي التنزيلات: <b>{dl}</b>\n👤 جدد اليوم: <b>{tu}</b>\n𖧷 ملفات اليوم: <b>{tf}</b>",
    "bc_ask": "⚑ <b>أرسل رسالة للبث:</b>",
    "bc_pre": "⚑ <b>معاينة البث</b>\n\nمحفوظ. اختر:",
    "bc_go": "⚑ <b>جارٍ الإرسال لـ {n}...</b>",
    "bc_done": "✧ <b>اكتمل!</b>\n\n✓ نجح: <b>{ok}</b>\n⨂ فشل: <b>{fail}</b>",
    "bc_btn_ask": "⎔ زر:\n<code>نص | URL</code>",
    "bc_btn_ok": "✧ تمت إضافة الزر: <b>{t}</b>",
    "bk_start": "⏳ جارٍ إنشاء نسخة...",
    "bk_done": "✧ <b>تم الإرسال!</b>",
    "ban_ask": "𖡎 أرسل ID للحظر:",
    "unban_ask": "✧ أرسل ID لإلغاء الحظر:",
    "banned_ok": "𖡎 <code>{uid}</code> محظور.",
    "unbanned_ok": "✧ <code>{uid}</code> ألغي حظره.",
    "uinfo": "👤 <b>معلومات</b>\n\nID: <code>{uid}</code>\nالاسم: {nm}\nاللغة: {lg}\nالملفات: {fc}\nالتنزيلات: {dl}\nالانضمام: {dt}\nمحظور: {bn}",
    "uid_ask": "👤 أرسل User ID:",
    "adel_ask": "◷ الحذف التلقائي (الحالي {c}):",
    "set_ok": "✧ الحذف التلقائي: <b>{m} دقيقة</b>",
    "set_panel": "𖣠 <b>{t}</b>\n\n◷ الحذف التلقائي: <b>{m} دقيقة</b>",
    "b_files":"𐙚 ملفاتي","b_search":"⌕ بحث","b_pub":"⌾ عامة","b_trend":"🔥 رائجة",
    "b_set":"𖣠 إعدادات","b_help":"⍰ مساعدة","b_lang":"⌾ اللغة","b_back":"⟵ رجوع",
    "b_close":"⨂ إغلاق","b_admin":"ᯓᡣ𐭩 المشرف","b_stats":"𖦹 إحصائيات","b_bc":"⚑ بث",
    "b_users":"𖠋 مستخدمون","b_bk":"⎘ نسخة","b_bset":"𖣠 إعدادات البوت","b_link":"⚲ رابط",
    "b_pw":"⚿ كلمة مرور","b_vis":"⊘ الرؤية","b_cap":"✐ عنوان","b_del":"␡ حذف",
    "b_fj":"⚑ انضمام إجباري","b_send":"⇪ إرسال","b_pin":"⌖ إرسال+تثبيت","b_addbtn":"⎔ زر",
    "b_cancel":"⊗ إلغاء","b_ban":"𖡎 حظر","b_unban":"✧ إلغاء حظر","b_info":"𖭣 معلومات",
    "b_yes":"✧ نعم","b_no":"⊗ لا","b_next":"⟶","b_prev":"⟵",
    "b_dl":"⤓ تنزيل","b_ch":"⚑ القناة","b_contact":"𖠿 المسؤول","b_skip":"⇥ تخطي",
    "b_verify":"✧ تحقق","b_mkpub":"⌾ عام","b_mkpriv":"⊘ خاص",
}
}

def t(uid, key, **kw):
    lang = db.get_lang(uid)
    if lang not in T: lang = "bn"
    txt = T[lang].get(key, T["en"].get(key, key))
    if kw:
        try: txt = txt.format(**kw)
        except: pass
    return txt

def tb(uid, key): return t(uid, key)

# ═══════════════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════════════

def lang_kb():
    rows = []
    items = list(LANG_FLAGS.items())
    for i in range(0, len(items), 2):
        row = []
        for code, flag in items[i:i+2]:
            row.append(btn(f"{flag} {LANG_NAMES[code]}", callback_data=f"lang:{code}", style=S_PRIMARY))
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def user_kb(uid):
    adm = is_admin(uid)
    rows = [
        [btn(tb(uid,"b_files"), "uf:0", style=S_PRIMARY),
         btn(tb(uid,"b_search"), "us", style=S_PRIMARY)],
        [btn(tb(uid,"b_pub"), "upf:0", style=S_SUCCESS),
         btn(tb(uid,"b_trend"), "ut", style=S_SUCCESS)],
        [btn(tb(uid,"b_set"), "uset"),
         btn(tb(uid,"b_help"), "uh")],
    ]
    if adm: rows.append([btn(tb(uid,"b_admin"), "ap", style=S_DANGER)])
    rows.append([btn(tb(uid,"b_close"), "close", style=S_DANGER)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admin_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn(tb(uid,"b_stats"), "as", style=S_PRIMARY), btn(tb(uid,"b_bc"), "abc", style=S_SUCCESS)],
        [btn(tb(uid,"b_users"), "au"), btn(tb(uid,"b_bk"), "abk", style=S_PRIMARY)],
        [btn(tb(uid,"b_bset"), "aset"), btn(tb(uid,"b_info"), "aui")],
        [btn(tb(uid,"b_back"), "up", style=S_DANGER)],
    ])

def file_kb(uid, fid):
    f = db.get_file(fid)
    if not f: return None
    vis = tb(uid,"b_mkpriv") if f.get("is_public") else tb(uid,"b_mkpub")
    pw_l = "⚿ ✧" if f.get("password") else tb(uid,"b_pw")
    fj_l = "⚑ ✧" if f.get("force_join") else tb(uid,"b_fj")
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn(tb(uid,"b_link"), f"fl:{fid}", style=S_SUCCESS), btn(pw_l, f"fp:{fid}")],
        [btn(vis, f"fv:{fid}", style=S_PRIMARY), btn(tb(uid,"b_cap"), f"fc:{fid}")],
        [btn(fj_l, f"ffj:{fid}"), btn(tb(uid,"b_del"), f"fd:{fid}", style=S_DANGER)],
        [btn(tb(uid,"b_back"), "uf:0", style=S_DANGER)],
    ])

def flist_kb(uid, files, page, pages, pfx):
    rows = []
    for fid, f in files:
        nm = (f.get("file_name","Untitled"))[:28]
        dl = f.get("downloads",0)
        rows.append([btn(f"𖧷 {nm} [{dl}↧]", f"fi:{fid}")])
    nav = []
    if page > 0: nav.append(btn(tb(uid,"b_prev"), f"{pfx}:{page-1}"))
    if page < pages-1: nav.append(btn(tb(uid,"b_next"), f"{pfx}:{page+1}"))
    if nav: rows.append(nav)
    rows.append([btn(tb(uid,"b_back"), "up", style=S_DANGER)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def finfo_text(uid, fid, f):
    vis = "⌾ Public" if f.get("is_public") else "⊘ Private"
    pw = "✧ Set" if f.get("password") else "𖹭 None"
    return t(uid, "file_saved", fn=esc(f.get("file_name","Untitled")),
             ft=f.get("file_type","?"), vis=vis, pw=pw,
             dl=f.get("downloads",0), dt=fmt_dt(f.get("upload_date","")))

def upanel_text(uid, name):
    u = db.get_user(uid)
    fc = u.get("files_count",0) if u else 0
    dl = u.get("total_downloads",0) if u else 0
    return t(uid, "welcome_back", bt=bf("Files Bro Bot"),
             name=esc(name), ss=sc("your stats"), fc=fc, dl=dl)

def get_ftype(msg: Message):
    if msg.document: return msg.document, 'document'
    if msg.video: return msg.video, 'video'
    if msg.photo: return msg.photo[-1], 'photo'
    if msg.audio: return msg.audio, 'audio'
    if msg.voice: return msg.voice, 'voice'
    if msg.video_note: return msg.video_note, 'video_note'
    if msg.animation: return msg.animation, 'animation'
    if msg.sticker: return msg.sticker, 'sticker'
    return None, None

# ═══════════════════════════════════════════════════════════════
#  ROUTER
# ═══════════════════════════════════════════════════════════════

router = Router()

async def schedule_delete(bot_obj: Bot, chat_id: int, file_msg_id: int, warn_msg_id: int, fid: str, uid: int, minutes: int):
    await asyncio.sleep(minutes * 60)
    try: await bot_obj.delete_message(chat_id, file_msg_id)
    except: pass
    if fid:
        link = f"https://t.me/{BOT_USERNAME}?start={fid}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_dl"), url=link, style=S_SUCCESS)]])
        try:
            await bot_obj.edit_message_text(
                chat_id=chat_id, message_id=warn_msg_id,
                text=f"<a href='{link}'>Deleted</a>",
                reply_markup=kb, disable_web_page_preview=True, parse_mode=ParseMode.HTML
            )
        except: pass

async def send_file(bot_obj: Bot, uid: int, fid: str, f: dict):
    try:
        sent = await bot_obj.copy_message(
            chat_id=uid, from_chat_id=FILE_CHANNEL,
            message_id=f["message_id"], caption=f.get("caption") or None,
            parse_mode=ParseMode.HTML
        )
        db.inc_fdl(fid)
        up = f.get("user_id")
        if up: db.inc_dl(up)

        mins = db.get_adel()
        link = f"https://t.me/{BOT_USERNAME}?start={fid}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_link"), url=link, style=S_SUCCESS)]])
        warn = await bot_obj.send_message(uid, t(uid,"adel_warn",m=mins), reply_markup=kb)
        asyncio.create_task(schedule_delete(bot_obj, uid, sent.message_id, warn.message_id, fid, uid, mins))
        return True
    except Exception as e:
        log.error(f"send_file err: {e}")
        try: await bot_obj.send_message(uid, t(uid,"not_found"))
        except: pass
        return False

# Commands
@router.message(CommandStart())
async def cmd_start(msg: Message, command: CommandObject):
    uid = msg.from_user.id
    if db.is_banned(uid):
        await msg.answer(t(uid,"banned"))
        return
    is_new = db.add_user(uid, msg.from_user.full_name)
    deep = command.args
    if deep:
        f = db.get_file(deep)
        if not f:
            await msg.answer(t(uid,"not_found"))
            return
        fj = f.get("force_join")
        if fj:
            try:
                member = await msg.bot.get_chat_member(chat_id=fj, user_id=uid)
                if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                    raise Exception("not member")
            except:
                ch_name = fj if fj.startswith("@") else f"@{fj}"
                ch_link = f"https://t.me/{fj.lstrip('@')}"
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [btn(tb(uid,"b_ch"), url=ch_link, style=S_PRIMARY)],
                    [btn(tb(uid,"b_verify"), callback_data=f"vfj:{deep}", style=S_SUCCESS)],
                ])
                await msg.answer(t(uid,"must_join",ch=ch_name), reply_markup=kb)
                return
        pw = f.get("password")
        if pw:
            set_state(uid, "check_pw", fid=deep)
            await msg.answer(t(uid,"enter_pw"))
            return
        await send_file(msg.bot, uid, deep, f)
        return

    if is_new or not db.get_user(uid).get("lang"):
        await msg.answer(t(uid,"welcome_new",bot=bf("Files Bro Bot")), reply_markup=lang_kb())
        return
    await msg.answer(upanel_text(uid, msg.from_user.full_name), reply_markup=user_kb(uid), disable_web_page_preview=True)

@router.message(Command("help"))
async def cmd_help(msg: Message):
    uid = msg.from_user.id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [btn(tb(uid,"b_ch"), url=SUPPORT_CHANNEL, style=S_PRIMARY), btn(tb(uid,"b_contact"), url=f"https://t.me/{ADMIN_CONTACT.lstrip('@')}")],
        [btn(tb(uid,"b_back"), "up", style=S_DANGER)],
    ])
    await msg.answer(t(uid,"help",t=bf("Help"),ch=SUPPORT_CHANNEL,ad=ADMIN_CONTACT), reply_markup=kb, disable_web_page_preview=True)

@router.message(Command("addadmin"))
async def cmd_addadmin(msg: Message, command: CommandObject):
    if int(msg.from_user.id) not in ADMIN_IDS: return
    if not command.args:
        await msg.answer("Usage: /addadmin <user_id>")
        return
    db.add_admin(command.args)
    await msg.answer(f"✧ Admin {command.args} added!")

@router.message(Command("rmadmin"))
async def cmd_rmadmin(msg: Message, command: CommandObject):
    if int(msg.from_user.id) not in ADMIN_IDS: return
    if not command.args:
        await msg.answer("Usage: /rmadmin <user_id>")
        return
    db.rm_admin(command.args)
    await msg.answer(f"✧ Admin {command.args} removed!")

@router.message(F.content_type.in_({"document","video","photo","audio","voice","video_note","animation","sticker"}))
async def handle_upload(msg: Message):
    uid = msg.from_user.id
    if db.is_banned(uid):
        await msg.answer(t(uid,"banned"))
        return
    db.add_user(uid, msg.from_user.full_name)
    
    st = get_state(uid)
    if st.get("action") == "bc_msg" and is_admin(uid):
        prompt_id = st.get("prompt_id")
        if prompt_id:
            try: await msg.bot.delete_message(uid, prompt_id)
            except: pass
        clear_state(uid)
        try:
            stored = await msg.bot.forward_message(FILE_CHANNEL, uid, msg.message_id)
            try: await msg.delete()
            except: pass
            bc_store[uid] = {"chat_id": FILE_CHANNEL, "msg_id": stored.message_id, "markup": None}
        except:
            bc_store[uid] = {"chat_id": uid, "msg_id": msg.message_id, "markup": None}
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [btn(tb(uid,"b_send"), "bs", style=S_SUCCESS), btn(tb(uid,"b_pin"), "bp", style=S_PRIMARY)],
            [btn(tb(uid,"b_addbtn"), "bb"), btn(tb(uid,"b_cancel"), "bx", style=S_DANGER)],
        ])
        await msg.answer(t(uid,"bc_pre"), reply_markup=kb)
        return

    fobj, ftype = get_ftype(msg)
    if not fobj: return
    fname = getattr(fobj, 'file_name', None) or f"{ftype}_{gen_id(4)}"
    caption = msg.html_text if msg.text else (msg.caption or "")
    
    user_log = f"👤 <b>{esc(msg.from_user.full_name)}</b> (<code>{uid}</code>)\n𖧷 {esc(fname)}\n{'─'*30}"
    ch_caption = f"{user_log}\n\n{caption}" if caption else user_log

    try:
        sent = await msg.bot.copy_message(
            chat_id=FILE_CHANNEL, from_chat_id=uid, message_id=msg.message_id,
            caption=ch_caption, parse_mode=ParseMode.HTML
        )
        fid = gen_id(10)
        db.save_file(fid, sent.message_id, uid, ftype, fname, caption)
        f = db.get_file(fid)
        link = f"https://t.me/{BOT_USERNAME}?start={fid}"
        text = finfo_text(uid, fid, f) + f"\n\n⚲ <code>{link}</code>"
        kb = file_kb(uid, fid)
        await msg.answer(text, reply_markup=kb, disable_web_page_preview=True)
    except Exception as e:
        await msg.answer(t(uid,"err"))

@router.message(F.text)
async def handle_text(msg: Message):
    uid = msg.from_user.id
    text = msg.text or ""
    st = get_state(uid)
    action = st.get("action")
    if not action: return

    prompt_id = st.get("prompt_id")
    if prompt_id:
        try: await msg.bot.delete_message(uid, prompt_id)
        except: pass

    if action == "check_pw":
        try: await msg.delete()
        except: pass
        fid = st.get("fid")
        f = db.get_file(fid)
        if not f:
            clear_state(uid)
            await msg.answer(t(uid,"not_found"))
            return
        if text.strip() == f.get("password"):
            clear_state(uid)
            await send_file(msg.bot, uid, fid, f)
        else:
            await msg.answer(t(uid,"wrong_pw"))
        return

    if action == "set_pw":
        try: await msg.delete()
        except: pass
        fid = st.get("fid")
        clear_state(uid)
        if text.strip().lower() == "remove":
            db.set_pw(fid, None)
            await msg.answer(t(uid,"pw_rm"))
        else:
            db.set_pw(fid, text.strip())
            await msg.answer(t(uid,"pw_set",pw=esc(text.strip())))
        return

    if action == "edit_cap":
        try: await msg.delete()
        except: pass
        fid = st.get("fid")
        clear_state(uid)
        cap = msg.html_text or text
        db.set_caption(fid, cap)
        f = db.get_file(fid)
        if f:
            try:
                uploader = db.get_user(f.get("user_id"))
                u_name = uploader.get("name", "Unknown") if uploader else "Unknown"
                user_log = f"👤 <b>{esc(u_name)}</b> (<code>{f.get('user_id')}</code>)\n𖧷 {esc(f.get('file_name', 'Untitled'))}\n{'─'*30}"
                ch_caption = f"{user_log}\n\n{cap}" if cap else user_log
                await msg.bot.edit_message_caption(FILE_CHANNEL, f["message_id"], caption=ch_caption, parse_mode=ParseMode.HTML)
            except: pass
        await msg.answer(t(uid,"cap_ok"))
        return

    if action == "set_fj":
        try: await msg.delete()
        except: pass
        fid = st.get("fid")
        clear_state(uid)
        if text.strip().lower() == "remove":
            db.set_fj(fid, None)
            await msg.answer(t(uid,"fj_rm"))
        else:
            ch = text.strip().lstrip("@")
            try:
                me = await msg.bot.get_me()
                bm = await msg.bot.get_chat_member(f"@{ch}", me.id)
                if bm.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                    await msg.answer(f"𖹭 <b>Bot is not an Admin!</b>\n\nঅনুগ্রহ করে প্রথমে বটকে ওই চ্যানেলে <b>Admin</b> হিসেবে যুক্ত করুন।", parse_mode="HTML")
                    return
            except Exception as e:
                err_str = str(e).lower()
                if "member list is inaccessible" in err_str or "chat not found" in err_str:
                    await msg.answer(f"𖹭 <b>Access Denied!</b>\n\nবট চ্যানেলটি খুঁজে পাচ্ছে না বা এক্সেস নেই।\nঅনুগ্রহ করে প্রথমে বটকে <b>@{ch}</b> চ্যানেলে <b>Admin</b> হিসেবে যুক্ত করুন।", parse_mode="HTML")
                else:
                    await msg.answer(f"𖹭 <b>Error:</b> {esc(str(e))}\n\nঅনুগ্রহ করে বটকে চ্যানেলে <b>Admin</b> দিন।", parse_mode="HTML")
                return
            db.set_fj(fid, f"@{ch}")
            await msg.answer(t(uid,"fj_set",ch=f"@{ch}"))
        return

    if action == "search":
        try: await msg.delete()
        except: pass
        clear_state(uid)
        q = text.strip()
        stype = st.get("stype","own")
        uid_f = uid if stype == "own" else None
        files, total = db.search(q, uid=uid_f)
        if not files:
            await msg.answer(t(uid,"no_res"))
            return
        r = t(uid,"search_res",n=total) + "\n\n"
        for fid, f in files:
            nm = (f.get("file_name",""))[:28]
            dl = f.get("downloads",0)
            link = f"https://t.me/{BOT_USERNAME}?start={fid}"
            r += f"𖧷 <b>{esc(nm)}</b> [{dl}↧]\n⚲ <a href='{link}'>Get</a>\n\n"
        await msg.answer(r, disable_web_page_preview=True)
        return

    if action == "bc_msg":
        clear_state(uid)
        try:
            stored = await msg.bot.forward_message(FILE_CHANNEL, uid, msg.message_id)
            try: await msg.delete()
            except: pass
            bc_store[uid] = {"chat_id": FILE_CHANNEL, "msg_id": stored.message_id, "markup": None}
        except:
            bc_store[uid] = {"chat_id": uid, "msg_id": msg.message_id, "markup": None}
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [btn(tb(uid,"b_send"), "bs", style=S_SUCCESS), btn(tb(uid,"b_pin"), "bp", style=S_PRIMARY)],
            [btn(tb(uid,"b_addbtn"), "bb"), btn(tb(uid,"b_cancel"), "bx", style=S_DANGER)],
        ])
        await msg.answer(t(uid,"bc_pre"), reply_markup=kb)
        return

    if action == "bc_btn":
        try: await msg.delete()
        except: pass
        clear_state(uid)
        parts = text.split("|", 1)
        if len(parts) != 2:
            await msg.answer("𖹭 Format: <code>Text | URL</code>")
            return
        bt, bu = parts[0].strip(), parts[1].strip()
        if not bu.startswith("http://") and not bu.startswith("https://"):
            bu = "https://" + bu
        bc = bc_store.get(uid, {})
        bc["markup"] = InlineKeyboardMarkup(inline_keyboard=[[btn(bt, url=bu, style=S_PRIMARY)]])
        bc_store[uid] = bc
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [btn(tb(uid,"b_send"), "bs", style=S_SUCCESS), btn(tb(uid,"b_pin"), "bp", style=S_PRIMARY)],
            [btn(tb(uid,"b_cancel"), "bx", style=S_DANGER)],
        ])
        await msg.answer(t(uid,"bc_btn_ok",t=esc(bt)), reply_markup=kb)
        return

    if action in ["ban", "unban", "uinfo", "set_adel"]:
        try: await msg.delete()
        except: pass
        clear_state(uid)
        try:
            val = int(text.strip())
            if action == "ban":
                db.ban(val)
                await msg.answer(t(uid,"banned_ok",uid=val))
            elif action == "unban":
                db.unban(val)
                await msg.answer(t(uid,"unbanned_ok",uid=val))
            elif action == "uinfo":
                u = db.get_user(val)
                if not u: await msg.answer("𖹭 Not found")
                else: await msg.answer(t(uid,"uinfo",uid=val,nm=esc(u.get("name","")),lg=u.get("lang","en"),fc=u.get("files_count",0),dl=u.get("total_downloads",0),dt=fmt_dt(u.get("join_date","")),bn="Yes" if db.is_banned(val) else "No"))
            elif action == "set_adel":
                if val < 1 or val > 1440: await msg.answer("𖹭 1-1440")
                else:
                    db.set_adel(val)
                    await msg.answer(t(uid,"set_ok",m=val))
        except:
            await msg.answer("𖹭 Invalid input")
        return

@router.callback_query()
async def cb_handler(cq: CallbackQuery):
    uid = cq.from_user.id
    data = cq.data
    try: await cq.answer()
    except: pass

    try:
        if data.startswith("lang:"):
            db.add_user(uid, cq.from_user.full_name)
            db.set_lang(uid, data.split(":")[1])
            await cq.message.edit_text(upanel_text(uid, cq.from_user.full_name), reply_markup=user_kb(uid), disable_web_page_preview=True)
            try: await cq.answer(t(uid, "lang_set"), show_alert=False)
            except: pass
            return

        if data == "close":
            try: await cq.message.delete()
            except: pass
            return

        if data == "up":
            await cq.message.edit_text(upanel_text(uid, cq.from_user.full_name), reply_markup=user_kb(uid), disable_web_page_preview=True)
            return

        if data.startswith("uf:"):
            pg = int(data.split(":")[1])
            files, total = db.user_files(uid, page=pg)
            pages = max(1, (total+7)//8)
            if not files:
                await cq.message.edit_text(t(uid,"no_files"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_back"),"up",style=S_DANGER)]]))
                return
            await cq.message.edit_text(t(uid,"my_hdr",p=pg+1,tp=pages), reply_markup=flist_kb(uid, files, pg, pages, "uf"), disable_web_page_preview=True)
            return

        if data.startswith("upf:"):
            pg = int(data.split(":")[1])
            files, total = db.public_files(page=pg)
            pages = max(1, (total+7)//8)
            if not files:
                await cq.message.edit_text(t(uid,"no_files"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_back"),"up",style=S_DANGER)]]))
                return
            await cq.message.edit_text(t(uid,"pub_hdr",p=pg+1,tp=pages), reply_markup=flist_kb(uid, files, pg, pages, "upf"), disable_web_page_preview=True)
            return

        if data == "ut":
            files = db.trending(10)
            if not files:
                await cq.message.edit_text(t(uid,"no_files"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_back"),"up",style=S_DANGER)]]))
                return
            txt = t(uid,"trend_hdr") + "\n\n"
            for i, (fid, f) in enumerate(files, 1):
                txt += f"{i}. 𖧷 <b>{esc(f.get('file_name','')[:26])}</b>\n   ↧ {f.get('downloads',0)} · <a href='https://t.me/{BOT_USERNAME}?start={fid}'>Get</a>\n\n"
            await cq.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_back"),"up",style=S_DANGER)]]), disable_web_page_preview=True)
            return

        if data == "us":
            set_state(uid, "search", stype="own", prompt_id=cq.message.message_id)
            await cq.message.edit_text(t(uid,"search_ask"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_cancel"),"up",style=S_DANGER)]]))
            return

        if data == "uset":
            lang = db.get_lang(uid)
            await cq.message.edit_text(f"𖣠 <b>{bf('Settings')}</b>\n\n⌾ Language: {LANG_FLAGS.get(lang,'⌾')} {LANG_NAMES.get(lang, lang)}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_lang"), "ulang", style=S_PRIMARY)],[btn(tb(uid,"b_back"), "up", style=S_DANGER)]]))
            return

        if data == "ulang":
            await cq.message.edit_text(t(uid,"welcome_new",bot=bf("Files Bro Bot")), reply_markup=lang_kb())
            return

        if data == "uh":
            kb = InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_ch"), url=SUPPORT_CHANNEL, style=S_PRIMARY), btn(tb(uid,"b_contact"), url=f"https://t.me/{ADMIN_CONTACT.lstrip('@')}")],[btn(tb(uid,"b_back"), "up", style=S_DANGER)]])
            await cq.message.edit_text(t(uid,"help",t=bf("Help"),ch=SUPPORT_CHANNEL,ad=ADMIN_CONTACT), disable_web_page_preview=True, reply_markup=kb)
            return

        if data.startswith("fi:"):
            fid = data[3:]
            f = db.get_file(fid)
            if not f:
                await cq.message.edit_text(t(uid,"not_found"))
                return
            link = f"https://t.me/{BOT_USERNAME}?start={fid}"
            txt = finfo_text(uid, fid, f) + f"\n\n⚲ <code>{link}</code>"
            if f["user_id"] == uid or is_admin(uid): kb = file_kb(uid, fid)
            else: kb = InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_dl"), url=link, style=S_SUCCESS)],[btn(tb(uid,"b_back"), "up", style=S_DANGER)]])
            await cq.message.edit_text(txt, reply_markup=kb, disable_web_page_preview=True)
            return

        if data.startswith("fl:"):
            fid = data[3:]
            await cq.message.bot.send_message(uid, f"⚲ <b>Link:</b>\n\n<code>https://t.me/{BOT_USERNAME}?start={fid}</code>", disable_web_page_preview=True)
            return

        if data.startswith("fp:"):
            fid = data[3:]
            f = db.get_file(fid)
            if not f or (f["user_id"]!=uid and not is_admin(uid)): return
            set_state(uid, "set_pw", fid=fid, prompt_id=cq.message.message_id)
            await cq.message.edit_text(t(uid,"ask_pw"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_cancel"),f"fi:{fid}",style=S_DANGER)]]))
            return

        if data.startswith("fv:"):
            fid = data[3:]
            f = db.get_file(fid)
            if not f or (f["user_id"]!=uid and not is_admin(uid)): return
            new_pub = not f.get("is_public", False)
            db.set_public(fid, new_pub)
            await cq.answer(t(uid, "pub_on" if new_pub else "pub_off"), show_alert=True)
            f = db.get_file(fid)
            await cq.message.edit_text(finfo_text(uid,fid,f)+f"\n\n⚲ <code>https://t.me/{BOT_USERNAME}?start={fid}</code>", reply_markup=file_kb(uid,fid), disable_web_page_preview=True)
            return

        if data.startswith("fc:"):
            fid = data[3:]
            f = db.get_file(fid)
            if not f or (f["user_id"]!=uid and not is_admin(uid)): return
            set_state(uid, "edit_cap", fid=fid, prompt_id=cq.message.message_id)
            await cq.message.edit_text(t(uid,"ask_cap"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_skip"),f"fi:{fid}")]]))
            return

        if data.startswith("ffj:"):
            fid = data[4:]
            f = db.get_file(fid)
            if not f or (f["user_id"]!=uid and not is_admin(uid)): return
            set_state(uid, "set_fj", fid=fid, prompt_id=cq.message.message_id)
            await cq.message.edit_text(t(uid,"ask_fj"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_cancel"),f"fi:{fid}",style=S_DANGER)]]))
            return

        if data.startswith("fd:"):
            fid = data[3:]
            f = db.get_file(fid)
            if not f or (f["user_id"]!=uid and not is_admin(uid)): return
            await cq.message.edit_text(t(uid,"del_confirm",fn=esc(f.get("file_name",""))), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_yes"),f"fdc:{fid}",style=S_DANGER), btn(tb(uid,"b_no"),f"fi:{fid}",style=S_SUCCESS)]]))
            return

        if data.startswith("fdc:"):
            fid = data[4:]
            f = db.get_file(fid)
            if not f or (f["user_id"]!=uid and not is_admin(uid)): return
            try: await cq.message.bot.delete_message(FILE_CHANNEL, f["message_id"])
            except: pass
            db.del_file(fid)
            await cq.message.edit_text(t(uid,"del_ok"))
            return

        if data.startswith("vfj:"):
            fid = data[4:]
            f = db.get_file(fid)
            if not f:
                await cq.message.edit_text(t(uid,"not_found"))
                return
            fj = f.get("force_join")
            if fj:
                try:
                    member = await cq.message.bot.get_chat_member(fj, uid)
                    if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                        raise Exception("no")
                except:
                    await cq.answer(t(uid,"must_join",ch=fj), show_alert=True)
                    return
            try: await cq.message.delete()
            except: pass
            if f.get("password"):
                set_state(uid, "check_pw", fid=fid)
                await cq.message.bot.send_message(uid, t(uid,"enter_pw"))
                return
            await cq.message.bot.send_message(uid, t(uid,"fj_ok"))
            await send_file(cq.message.bot, uid, fid, f)
            return

        # ADMIN
        if not is_admin(uid): return

        if data == "ap":
            await cq.message.edit_text(t(uid,"ap",t=bf("Admin Panel"),u=db.user_count(),f=db.file_count(),dl=db.total_dl(),tu=db.today_users(),tf=db.today_files()), reply_markup=admin_kb(uid))
            return

        if data == "as":
            await cq.message.edit_text(t(uid,"stats",t=bf("Statistics"),u=db.user_count(),f=db.file_count(),dl=db.total_dl(),tu=db.today_users(),tf=db.today_files()), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_back"),"ap",style=S_DANGER)]]))
            return

        if data == "abc":
            set_state(uid, "bc_msg", prompt_id=cq.message.message_id)
            await cq.message.edit_text(t(uid,"bc_ask"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_cancel"),"ap",style=S_DANGER)]]))
            return

        if data in ("bs", "bp"):
            bc = bc_store.get(uid)
            if not bc:
                await cq.message.edit_text("𖹭 No message stored.")
                return
            await cq.message.edit_text(t(uid,"bc_go",n=db.user_count()))
            asyncio.create_task(do_broadcast(cq.message.bot, uid, bc, data=="bp"))
            bc_store.pop(uid, None)
            return

        if data == "bb":
            set_state(uid, "bc_btn", prompt_id=cq.message.message_id)
            await cq.message.edit_text(t(uid,"bc_btn_ask"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_cancel"),"ap",style=S_DANGER)]]))
            return

        if data == "bx":
            bc_store.pop(uid, None)
            clear_state(uid)
            await cq.message.edit_text(t(uid,"ap",t=bf("Admin Panel"),u=db.user_count(),f=db.file_count(),dl=db.total_dl(),tu=db.today_users(),tf=db.today_files()), reply_markup=admin_kb(uid))
            return

        if data == "au":
            await cq.message.edit_text(f"𖠋 <b>{bf('User Management')}</b>\n\n𖠋 Total: <b>{db.user_count()}</b>\n𖡎 Banned: <b>{len(db.d.get('banned',[]))}</b>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_ban"), "aban", style=S_DANGER), btn(tb(uid,"b_unban"), "aubn", style=S_SUCCESS)],[btn(tb(uid,"b_info"), "aui")],[btn(tb(uid,"b_back"), "ap", style=S_DANGER)]]))
            return

        if data == "aban":
            set_state(uid, "ban", prompt_id=cq.message.message_id)
            await cq.message.edit_text(t(uid,"ban_ask"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_cancel"),"au",style=S_DANGER)]]))
            return

        if data == "aubn":
            set_state(uid, "unban", prompt_id=cq.message.message_id)
            await cq.message.edit_text(t(uid,"unban_ask"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_cancel"),"au",style=S_DANGER)]]))
            return

        if data == "aui":
            set_state(uid, "uinfo", prompt_id=cq.message.message_id)
            await cq.message.edit_text(t(uid,"uid_ask"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_cancel"),"au",style=S_DANGER)]]))
            return

        if data == "abk":
            await cq.message.edit_text(t(uid,"bk_start"))
            try:
                jb = json.dumps(db.backup_data(), ensure_ascii=False, indent=2).encode("utf-8")
                fn = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                cap = f"⎘ <b>Backup</b>\n𖧹 {datetime.datetime.now().strftime('%d %b %Y %H:%M')}\n𖠋 {db.user_count()} · 𐙚 {db.file_count()}"
                await cq.message.bot.send_document(BACKUP_CHANNEL, BufferedInputFile(jb, filename=fn), caption=cap, parse_mode=ParseMode.HTML)
                await cq.message.bot.send_document(uid, BufferedInputFile(jb, filename=fn), caption=cap, parse_mode=ParseMode.HTML)
                await cq.message.edit_text(t(uid,"bk_done"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_back"),"ap",style=S_DANGER)]]))
            except Exception as e:
                await cq.message.edit_text(f"𖹭 Backup failed: {esc(str(e))}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_back"),"ap",style=S_DANGER)]]))
            return

        if data == "aset":
            m = db.get_adel()
            await cq.message.edit_text(t(uid,"set_panel",t=bf("Bot Settings"),m=m), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(f"◷ Auto-Delete: {m}m", "aset_ad", style=S_PRIMARY)],[btn(tb(uid,"b_back"), "ap", style=S_DANGER)]]))
            return

        if data == "aset_ad":
            set_state(uid, "set_adel", prompt_id=cq.message.message_id)
            await cq.message.edit_text(t(uid,"adel_ask",c=db.get_adel()), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn(tb(uid,"b_cancel"),"aset",style=S_DANGER)]]))
            return

    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower(): log.error(f"CB err: {e}")
    except Exception as e:
        log.error(f"CB err: {e}")

async def do_broadcast(bot_obj: Bot, admin_uid: int, bc: dict, pin: bool):
    uids = db.all_uids()
    ok = fail = 0
    for uid in uids:
        try:
            sent = await bot_obj.copy_message(uid, bc["chat_id"], bc["msg_id"], reply_markup=bc.get("markup"))
            if pin:
                try: await bot_obj.pin_chat_message(uid, sent.message_id, disable_notification=True)
                except: pass
            ok += 1
        except:
            fail += 1
        await asyncio.sleep(0.05)
    try: await bot_obj.send_message(admin_uid, t(admin_uid,"bc_done",ok=ok,fail=fail))
    except: pass

async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    log.info(f"Bot @{BOT_USERNAME} starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Start the bot"),
        types.BotCommand(command="help", description="Get help"),
    ])
    await dp.start_polling(bot, allowed_updates=["message","callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
