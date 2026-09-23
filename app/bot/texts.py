TEXTS = {
    "welcome": {
        "bn": "👋 স্বাগতম, {name}!\n\n<b>RBX404 ডিজিটাল ফাইল প্ল্যাটফর্মে</b> তোমাকে স্বাগতম।\n\n"
              "📤 যেকোনো ফাইল/ভিডিও/মেসেজ পাঠাও — সাথে সাথে একটা সিকিউর শেয়ার লিংক পাবে।\n"
              "📱 নিচের বাটনে Mini App খুলে ফাইল ম্যানেজ করো।",
        "en": "👋 Welcome, {name}!\n\n<b>RBX404 Digital File Platform</b>\n\n"
              "📤 Send any file/video/message — get an instant secure share link.\n"
              "📱 Open the Mini App below to manage your files.",
    },
    "open_app": {"bn": "🌐 Mini App খুলুন", "en": "🌐 Open Mini App"},
    "help": {
        "bn": "❓ <b>সাহায্য</b>\n\n"
              "• ফাইল/ভিডিও/অডিও/ডকুমেন্ট পাঠাও → লিংক পাবে\n"
              "• মেসেজ ফরওয়ার্ড করলেও লিংক তৈরি হবে\n"
              "• Mini App থেকে ফোল্ডার, ফেভারিট, কালেকশন, ট্র্যাশ ম্যানেজ করো\n"
              "• /start — শুরু করুন\n• /help — এই মেসেজ",
        "en": "❓ <b>Help</b>\n\n"
              "• Send any file/video/audio/document → get a link\n"
              "• Forward a message too — a link gets generated\n"
              "• Manage folders, favorites, collections, trash from the Mini App\n"
              "• /start — begin\n• /help — this message",
    },
    "file_saved": {
        "bn": "✅ <b>ফাইল সেভ হয়েছে!</b>\n\n📄 {name}\n💾 {size}\n\n🔗 আপনার লিংক নিচে 👇",
        "en": "✅ <b>File saved!</b>\n\n📄 {name}\n💾 {size}\n\n🔗 Your link is below 👇",
    },
    "copy_link": {"bn": "📋 লিংক কপি", "en": "📋 Copy Link"},
    "qr_code": {"bn": "▣ QR কোড", "en": "▣ QR Code"},
    "settings": {"bn": "⚙️ সেটিংস", "en": "⚙️ Settings"},
    "not_verified": {
        "bn": "🔐 <b>এক্সেস ভেরিফিকেশন</b>\n\nRBX404 ব্যবহার করতে নিচের সবগুলোতে জয়েন করুন, "
              "তারপর ভেরিফাই বাটনে চাপুন।",
        "en": "🔐 <b>Access Verification</b>\n\nJoin all of the following to use RBX404, "
              "then tap Verify.",
    },
    "verify_btn": {"bn": "🔄 ভেরিফাই মেম্বারশিপ", "en": "🔄 Verify Membership"},
    "verify_fail": {
        "bn": "❌ এখনো সব জায়গায় জয়েন করেননি। জয়েন করে আবার চেষ্টা করুন।",
        "en": "❌ You haven't joined everything yet. Join and try again.",
    },
    "verify_ok": {"bn": "✅ ভেরিফাইড! এখন বট ব্যবহার করতে পারবেন।",
                  "en": "✅ Verified! You can use the bot now."},
    "banned": {"bn": "🚫 আপনাকে ব্যান করা হয়েছে।", "en": "🚫 You are banned from this bot."},
    "file_gone": {"bn": "❌ ফাইলটি পাওয়া যায়নি বা মেয়াদ শেষ হয়ে গেছে।",
                  "en": "❌ File not found or has expired."},
    "file_limit": {"bn": "❌ ডাউনলোড লিমিট শেষ হয়ে গেছে।",
                   "en": "❌ Download limit reached."},
    "file_disabled": {"bn": "⛔ এই লিংকটি নিষ্ক্রিয় করা হয়েছে।", "en": "⛔ This link is disabled."},
    "need_join_file": {
        "bn": "🔐 এই ফাইল পেতে {ch} জয়েন করুন, তারপর লিংকে আবার ক্লিক করুন।",
        "en": "🔐 Join {ch} to get this file, then tap the link again.",
    },
    "admin_only": {"bn": "⛔ শুধু অ্যাডমিনদের জন্য।", "en": "⛔ Admins only."},
    "maintenance": {"bn": "🛠 বট রক্ষণাবেক্ষণের জন্য সাময়িক বন্ধ আছে।",
                     "en": "🛠 Bot is temporarily under maintenance."},
}


def t(lang, key, **kw):
    lang = lang if lang in ("bn", "en") else "bn"
    s = TEXTS.get(key, {}).get(lang) or TEXTS.get(key, {}).get("en") or key
    try:
        return s.format(**kw)
    except Exception:
        return s
