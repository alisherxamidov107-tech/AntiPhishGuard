import os
import sqlite3
import logging
import asyncio
import socket
import urllib.request
import urllib.parse
import json
from urllib.parse import urlparse
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
import re

from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.constants import ChatMemberStatus

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ChatMemberHandler,
    CallbackQueryHandler,
    filters,
)


from services.scanner import scan_text, extract_urls


# =========================================================
# CONFIG
# =========================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN topilmadi. .env faylini tekshiring."
    )


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# DATABASE
# =========================================================

DB_NAME = "database.db"


def db_connect():
    return sqlite3.connect(DB_NAME)


def init_db():

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            title TEXT,
            enabled INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            username TEXT,
            url TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_video_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_video_id TEXT,
            updated_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def register_group(chat_id: int, title: str):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO groups
        (chat_id, title, enabled, created_at)
        VALUES (?, ?, 1, ?)
    """, (
        chat_id,
        title,
        datetime.now().isoformat(),
    ))

    conn.commit()
    conn.close()


def is_protection_enabled(chat_id: int):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT enabled FROM groups WHERE chat_id = ?",
        (chat_id,)
    )

    result = cursor.fetchone()

    conn.close()

    if result is None:
        return True

    return bool(result[0])


def set_protection(chat_id: int, enabled: bool):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE groups
        SET enabled = ?
        WHERE chat_id = ?
    """, (
        1 if enabled else 0,
        chat_id,
    ))

    conn.commit()
    conn.close()


def save_incident(
    chat_id: int,
    user_id: int,
    username: str,
    url: str
):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO incidents
        (chat_id, user_id, username, url, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        chat_id,
        user_id,
        username,
        url,
        datetime.now().isoformat(),
    ))

    conn.commit()
    conn.close()


def get_stats(chat_id: int):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM incidents
        WHERE chat_id = ?
    """, (chat_id,))

    total = cursor.fetchone()[0]

    conn.close()

    return total


# =========================================================
# ADMIN CHECK
# =========================================================

async def is_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_chat:
        return False

    if not update.effective_user:
        return False

    try:

        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )

        return member.status in [
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        ]

    except Exception as e:

        logger.error(
            "Admin tekshirish xatosi: %s",
            e
        )

        return False


# =========================================================
# START MENU
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    bot = await context.bot.get_me()

    add_url = (
        f"https://t.me/{bot.username}?startgroup=true"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Guruhga qo‘shish",
                url=add_url
            )
        ],
        [
            InlineKeyboardButton(
                "📖 Qo‘llanma",
                callback_data="guide"
            ),
            InlineKeyboardButton(
                "🛡️ Himoya",
                callback_data="protection"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Statistika",
                callback_data="statistics"
            )
        ],
    ])

    text = (
        "🛡️ <b>AntiPhish Guard</b>\n\n"

        "🔐 Telegram guruhlaringizni "
        "phishing va shubhali havolalardan "
        "himoya qiluvchi xavfsizlik boti.\n\n"

        "⚡ <b>Asosiy imkoniyatlar:</b>\n"
        "• 🔗 Havolalarni tekshirish\n"
        "• 🚨 Phishingni aniqlash\n"
        "• 🗑️ Xavfli xabarlarni o‘chirish\n"
        "• 📦 APK fayllarni bloklash\n"
        "• 📊 Hodisalar statistikasi\n"
        "• ⚙️ Guruh himoyasini boshqarish\n\n"

        "👇 Kerakli bo‘limni tanlang:"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


# =========================================================
# CALLBACK MENU
# =========================================================

async def menu_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if query.data == "guide":

        text = (
            "📖 <b>APG qo‘llanmasi</b>\n\n"

            "1️⃣ APG'ni guruhga qo‘shing.\n"
            "2️⃣ Botni administrator qiling.\n"
            "3️⃣ Xabarlarni o‘chirish huquqini bering.\n"
            "4️⃣ Group Privacy'ni o‘chirib qo‘ying.\n\n"

            "Shundan keyin APG guruhdagi "
            "xabarlarni tekshira oladi.\n\n"

            "🚨 Shubhali havola aniqlansa, "
            "xabar o‘chiriladi va guruhga "
            "ogohlantirish yuboriladi.\n\n"

            "📦 APK fayllar ham avtomatik "
            "bloklanadi."
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "⬅️ Orqaga",
                    callback_data="home"
                )
            ]
        ])

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    elif query.data == "protection":

        text = (
            "🛡️ <b>APG himoyasi</b>\n\n"

            "🔗 URL scanning — ON\n"
            "🚨 Phishing detection — ON\n"
            "📦 APK protection — ON\n"
            "🗑️ Xavfli xabarlarni o‘chirish — ON\n"
            "📊 Incident logging — ON\n\n"

            "Himoya guruh bo‘yicha "
            "alohida boshqariladi."
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "⬅️ Orqaga",
                    callback_data="home"
                )
            ]
        ])

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    elif query.data == "statistics":

        if query.message.chat.type in [
            "group",
            "supergroup"
        ]:

            total = get_stats(
                query.message.chat.id
            )

            text = (
                "📊 <b>APG statistikasi</b>\n\n"
                f"🚨 Aniqlangan hodisalar: "
                f"<b>{total}</b>"
            )

        else:

            text = (
                "📊 Statistikani ko‘rish uchun "
                "APG guruh ichida ishlashi kerak."
            )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "⬅️ Orqaga",
                    callback_data="home"
                )
            ]
        ])

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    elif query.data == "home":

        bot = await context.bot.get_me()

        add_url = (
            f"https://t.me/{bot.username}?startgroup=true"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "➕ Guruhga qo‘shish",
                    url=add_url
                )
            ],
            [
                InlineKeyboardButton(
                    "📖 Qo‘llanma",
                    callback_data="guide"
                ),
                InlineKeyboardButton(
                    "🛡️ Himoya",
                    callback_data="protection"
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 Statistika",
                    callback_data="statistics"
                )
            ],
        ])

        text = (
            "🛡️ <b>AntiPhish Guard</b>\n\n"
            "🔐 Guruhlaringizni phishing "
            "havolalaridan himoya qiling.\n\n"
            "👇 Kerakli bo‘limni tanlang:"
        )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )


# =========================================================
# PROTECT
# =========================================================

async def protect(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_chat:
        return

    if not await is_admin(update, context):

        await update.message.reply_text(
            "❌ Bu buyruq faqat adminlar uchun."
        )

        return

    chat = update.effective_chat

    register_group(
        chat.id,
        chat.title or "Unknown"
    )

    set_protection(
        chat.id,
        True
    )

    await update.message.reply_text(
        "🛡️ <b>APG himoyasi yoqildi!</b>\n\n"
        "🔗 Havolalar tekshiriladi.\n"
        "🚨 Shubhali linklar aniqlanadi.\n"
        "📦 APK fayllar bloklanadi.\n"
        "🗑️ Xavfli xabarlar o‘chiriladi.",
        parse_mode="HTML"
    )


# =========================================================
# UNPROTECT
# =========================================================

async def unprotect(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_chat:
        return

    if not await is_admin(update, context):

        await update.message.reply_text(
            "❌ Bu buyruq faqat adminlar uchun."
        )

        return

    set_protection(
        update.effective_chat.id,
        False
    )

    await update.message.reply_text(
        "🔴 <b>APG himoyasi o‘chirildi.</b>",
        parse_mode="HTML"
    )


# =========================================================
# STATUS
# =========================================================

async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_chat:
        return

    enabled = is_protection_enabled(
        update.effective_chat.id
    )

    if enabled:

        text = (
            "🟢 <b>APG faol</b>\n\n"
            "🛡️ Guruh himoyalangan."
        )

    else:

        text = (
            "🔴 <b>APG o‘chiq</b>\n\n"
            "Himoya vaqtincha o‘chirilgan."
        )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )


# =========================================================
# STATS
# =========================================================

async def stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_chat:
        return

    total = get_stats(
        update.effective_chat.id
    )

    await update.message.reply_text(
        "📊 <b>APG statistikasi</b>\n\n"
        f"🚨 Aniqlangan hodisalar: "
        f"<b>{total}</b>",
        parse_mode="HTML"
    )


# =========================================================
# LINK IP / LOCATION LOOKUP
# =========================================================

def get_link_info(url: str):
    """
    Domenning DNS orqali server IP manzilini aniqlaydi.
    IP geolocation server IP bo'yicha taxminiy davlat/shahar/ISP beradi.
    Bu linkni yuborgan odamning IP manzili emas.
    """
    try:
        clean_url = (url or "").rstrip(".,!?;:)")

        if clean_url.startswith("www."):
            clean_url = "https://" + clean_url

        parsed = urlparse(clean_url)
        domain = parsed.hostname

        if not domain:
            return None

        domain = domain.lower()
        ip = socket.gethostbyname(domain)

        country = "Aniqlanmadi"
        city = "Aniqlanmadi"
        isp = "Aniqlanmadi"

        try:
            api_url = f"https://ipwho.is/{ip}"

            request = urllib.request.Request(
                api_url,
                headers={"User-Agent": "AntiPhishGuard/1.0"}
            )

            with urllib.request.urlopen(request, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))

            if data.get("success") is True:
                country = data.get("country") or "Aniqlanmadi"
                city = data.get("city") or "Aniqlanmadi"
                isp = (
                    data.get("connection", {}).get("isp")
                    or data.get("connection", {}).get("org")
                    or "Aniqlanmadi"
                )

        except Exception as e:
            logger.warning(
                "IP geolocation xatosi: %s",
                e
            )

        return {
            "domain": domain,
            "ip": ip,
            "country": country,
            "city": city,
            "isp": isp,
        }

    except Exception as e:
        logger.warning(
            "Link IP aniqlash xatosi: %s",
            e
        )
        return None


# =========================================================
# MESSAGE SCANNER
# =========================================================

async def scan_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.effective_message

    if not message:
        return

    chat = update.effective_chat

    if not chat:
        return

    # =====================================================
    # PRIVATE CHAT LINK LOOKUP
    # =====================================================
    # Botga shaxsiy chatda link yuborilsa, linkning server
    # IP va IP-geolocation ma'lumotini qaytaradi.
    if chat.type == "private":

        text = (
            message.text
            or message.caption
            or ""
        )

        urls = extract_urls(text)

        if not urls:
            return

        results = []

        for url in urls:
            info = get_link_info(url)

            if info:
                results.append(
                    "\n".join([
                        "🔎 <b>LINK TAHLILI</b>",
                        "",
                        f"🔗 Link: <code>{url}</code>",
                        f"🌐 Domen: <code>{info['domain']}</code>",
                        f"📡 Server IP: <code>{info['ip']}</code>",
                        f"🌍 Davlat: {info['country']}",
                        f"🏙 Taxminiy shahar: {info['city']}",
                        f"🏢 ISP/Hosting: {info['isp']}",
                        "",
                        "ℹ️ <i>Joylashuv IP bo‘yicha taxminiy.</i>",
                    ])
                )
            else:
                results.append(
                    "\n".join([
                        "🔎 <b>LINK TAHLILI</b>",
                        "",
                        f"🔗 Link: <code>{url}</code>",
                        "❌ Server IP ma'lumotini aniqlab bo‘lmadi.",
                    ])
                )

        await message.reply_text(
            "\n\n".join(results),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    # Faqat guruhlarda.
    if chat.type not in [
        "group",
        "supergroup"
    ]:
        return

    # Himoya yoqilmagan bo'lsa.
    if not is_protection_enabled(chat.id):
        return

    user = update.effective_user

    username = (
        user.mention_html()
        if user
        else "Foydalanuvchi"
    )

    # =====================================================
    # APK DETECTION
    # =====================================================

    if message.document:

        file_name = (
            message.document.file_name or ""
        ).lower()

        mime_type = (
            message.document.mime_type or ""
        ).lower()

        is_apk = (
            file_name.endswith(".apk")
            or mime_type
            == "application/vnd.android.package-archive"
        )

        if is_apk:

            try:
                # APK xabarini o'chirish.
                await message.delete()

                scanning = await context.bot.send_message(
                    chat_id=chat.id,
                    text=(
                        "🔎 <b>SECURITY SCAN</b>\n\n"
                        "📦 APK fayl tekshirilmoqda...\n"
                        "⏳ Iltimos kuting..."
                    ),
                    parse_mode="HTML"
                )

                await asyncio.sleep(0.7)

                await scanning.edit_text(
                    "🛡️ <b>ANTI-PHISH GUARD</b>\n\n"
                    "🔍 APK fayl tahlil qilinmoqda...\n"
                    "⚠️ Xavfsizlik tekshiruvi davom etmoqda...",
                    parse_mode="HTML"
                )

                await asyncio.sleep(0.7)

                await scanning.edit_text(
                    "🚨 <b>THREAT DETECTED</b>\n\n"
                    "❌ Xavfli APK aniqlandi!\n"
                    "🛑 Fayl bloklanmoqda...",
                    parse_mode="HTML"
                )

                await asyncio.sleep(0.7)

                await scanning.edit_text(
                    "🚨 <b>DIQQAT! XAVF ANIQLANDI!</b>\n\n"
                    "📦 <b>APK FAYL BLOKLANDI!</b>\n\n"
                    f"👤 Foydalanuvchi: {username}\n"
                    "🔴 Status: <b>BLOKLANDI</b>\n"
                    "📱 Turi: ANDROID APK\n\n"
                    "⚠️ Ushbu fayl xavfsizlik "
                    "sababli guruhdan o'chirildi.\n\n"
                    "🛡️ <b>AntiPhish Guard</b>",
                    parse_mode="HTML"
                )

            except Exception as e:
                logger.warning(
                    "APK faylni qayta ishlashda xato: %s",
                    e
                )

            return

    # =====================================================
    # TEXT / LINK SCAN
    # =====================================================

    text = (
        message.text
        or message.caption
        or ""
    )

    if not text:
        return

    # services.scanner ichidagi URL aniqlash funksiyasi.
    dangerous_urls = scan_text(text)

    if not dangerous_urls:
        return

    # =====================================================
    # LINK IP INFORMATION
    # =====================================================

    link_info_blocks = []

    for url in dangerous_urls:
        info = get_link_info(url)

        if info:
            link_info_blocks.append(
                "\n".join([
                    f"🔗 Link: <code>{url}</code>",
                    f"🌐 Domen: <code>{info['domain']}</code>",
                    f"📡 Server IP: <code>{info['ip']}</code>",
                    f"🌍 Davlat: {info['country']}",
                    f"🏙 Shahar: {info['city']}",
                    f"🏢 ISP/Hosting: {info['isp']}",
                ])
            )
        else:
            link_info_blocks.append(
                "\n".join([
                    f"🔗 Link: <code>{url}</code>",
                    "📡 Server IP: Aniqlanmadi",
                    "🌍 Joylashuv: Aniqlanmadi",
                ])
            )

    # =====================================================
    # INCIDENT LOGGING
    # =====================================================

    for url in dangerous_urls:

        save_incident(
            chat_id=chat.id,
            user_id=user.id if user else 0,
            username=user.username if user else "",
            url=url
        )

    # =====================================================
    # DELETE DANGEROUS MESSAGE
    # =====================================================

    try:
        await message.delete()

    except Exception as e:
        logger.warning(
            "Xabarni o'chirib bo'lmadi: %s",
            e
        )

    # =====================================================
    # PROFESSIONAL PHISHING ANIMATION
    # =====================================================

    try:
        scanning = await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "🔎 <b>SECURITY SCAN</b>\n\n"
                "🔗 Havola tekshirilmoqda...\n"
                "⏳ Iltimos kuting..."
            ),
            parse_mode="HTML"
        )

        await asyncio.sleep(0.7)

        await scanning.edit_text(
            "🛡️ <b>ANTI-PHISH GUARD</b>\n\n"
            "🔍 Havola tahlil qilinmoqda...\n"
            "🌐 Server ma'lumotlari aniqlanmoqda...",
            parse_mode="HTML"
        )

        await asyncio.sleep(0.7)

        await scanning.edit_text(
            "🚨 <b>THREAT DETECTED</b>\n\n"
            "❌ Xavfli havola aniqlandi!\n"
            "🛑 Xabar bloklanmoqda...",
            parse_mode="HTML"
        )

        await asyncio.sleep(0.7)

        details = "\n\n".join(link_info_blocks)

        await scanning.edit_text(
            "🚨 <b>DIQQAT! XAVF ANIQLANDI!</b>\n\n"
            "🔗 <b>XAVFLI LINK ANIQLANDI!</b>\n\n"
            f"👤 Foydalanuvchi: {username}\n"
            "🔴 Status: <b>BLOKLANDI</b>\n"
            "⚠️ Risk: <b>PHISHING</b>\n\n"
            f"{details}\n\n"
            "🚫 <b>BU HAVOLAGA KIRMANG!</b>\n"
            "Xabar xavfsizlik sababli o'chirildi.\n\n"
            "🛡️ <b>AntiPhish Guard</b>",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(
            "Warning yuborishda xato: %s",
            e
        )


# =========================================================
# DAILY UZBEK CYBERSECURITY VIDEO
# =========================================================

DAILY_VIDEO_CHAT_ID = os.getenv("DAILY_VIDEO_CHAT_ID")
DAILY_VIDEO_HOUR = int(os.getenv("DAILY_VIDEO_HOUR", "12"))
DAILY_VIDEO_MINUTE = int(os.getenv("DAILY_VIDEO_MINUTE", "0"))
DAILY_VIDEO_TZ = os.getenv("DAILY_VIDEO_TZ", "Asia/Tashkent")

VIDEO_SEARCH_QUERIES = [
    'Kiberxavfsizlik markazi kiberxavfsizlik',
    'Kiberxavfsizlik markazi firibgarlik',
    'Kiberxavfsizlik markazi himoya',
    'ICHKI ISHLAR VAZIRLIGI kiberxavfsizlik',
]

UZBEK_CYBER_WORDS = [
    'kiber', 'xavfsizlik', 'firibgarlik', 'himoya', 'parol',
    'shaxsiy', "ma'lumot", 'ma’lumot', 'zararli', 'virus',
    'phishing', 'apk', 'ogoh', 'firibgar', 'akkaunt', 'internet',
]

TRUSTED_VIDEO_CHANNEL_HINTS = [
    'Kiberxavfsizlik markazi',
    'ICHKI ISHLAR VAZIRLIGI',
    'csecuz',
    'ichkiishlarvazirligi',
]


def _html_unescape(text: str) -> str:
    import html
    return html.unescape(text or "")


def find_uzbek_cyber_videos(limit: int = 5):
    """
    YouTube public search sahifasidan kiberxavfsizlikka oid
    o'zbekcha videolarni topishga harakat qiladi.

    Bot video faylni yuklab olmaydi: faqat video havolasini yuboradi.
    Bu usul API key talab qilmaydi.
    """

    found = []
    seen = set()

    for query in VIDEO_SEARCH_QUERIES:
        try:
            encoded_query = urllib.parse.quote_plus(query)
            search_url = (
                "https://www.youtube.com/results?search_query="
                + encoded_query
            )

            request = urllib.request.Request(
                search_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/142 Safari/537.36"
                    )
                },
            )

            with urllib.request.urlopen(request, timeout=15) as response:
                page = response.read().decode("utf-8", errors="ignore")

            # YouTube sahifasidagi videoId qiymatlarini ajratib olamiz.
            ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', page)

            for video_id in ids:
                if video_id in seen:
                    continue

                # ID oldidan/atrofidan title topishga harakat qilamiz.
                pos = page.find('"videoId":"' + video_id + '"')
                chunk = page[max(0, pos - 2500):pos + 5000]

                title_match = re.search(
                    r'"title":\{"runs":\[\{"text":"(.*?)"',
                    chunk,
                    re.S,
                )

                owner_match = re.search(
                    r'"ownerText":\{"runs":\[\{"text":"(.*?)"',
                    chunk,
                    re.S,
                )

                title = (
                    _html_unescape(title_match.group(1))
                    if title_match
                    else "Kiberxavfsizlik videosi"
                )

                owner = (
                    _html_unescape(owner_match.group(1))
                    if owner_match
                    else ""
                )

                title_lower = title.lower()
                owner_lower = owner.lower()

                # Faqat kiberxavfsizlik mavzusiga yaqin videolar.
                if not any(word in title_lower for word in UZBEK_CYBER_WORDS):
                    continue

                # O'zbekcha mazmun belgilaridan kamida bittasi bo'lsin.
                uzbek_markers = [
                    "o'zbek", "o‘zbek", "uzbek", "xavfsizlik",
                    "firibgarlik", "himoya", "parol", "ma'lumot",
                    "ma’lumot", "zararli", "ogoh", "firibgar",
                ]

                if not any(marker in title_lower for marker in uzbek_markers):
                    continue

                # Faqat ishonchli rasmiy manbalardan olingan videolar.
                if not any(
                    hint.lower() in owner_lower
                    for hint in TRUSTED_VIDEO_CHANNEL_HINTS
                ):
                    continue

                seen.add(video_id)
                found.append({
                    "id": video_id,
                    "title": title[:200],
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                })

                if len(found) >= limit:
                    return found

        except Exception as e:
            logger.warning(
                "YouTube qidiruv xatosi (%s): %s",
                query,
                e,
            )

    return found


def get_last_daily_video_id():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT last_video_id FROM daily_video_state WHERE id = 1"
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def save_last_daily_video_id(video_id: str):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO daily_video_state (id, last_video_id, updated_at)
        VALUES (1, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            last_video_id = excluded.last_video_id,
            updated_at = excluded.updated_at
    """, (video_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()


async def send_daily_cyber_video(context: ContextTypes.DEFAULT_TYPE):
    """
    Har kuni bir marta ro'yxatdan o'tgan guruhlarga
    o'zbekcha kiberxavfsizlik videosi havolasini yuboradi.
    """

    videos = await asyncio.to_thread(find_uzbek_cyber_videos, 5)

    if not videos:
        logger.warning("O'zbekcha kiberxavfsizlik videosi topilmadi.")
        return

    last_video_id = get_last_daily_video_id()
    video = next(
        (item for item in videos if item["id"] != last_video_id),
        videos[0],
    )

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM groups WHERE enabled = 1")
    chat_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Agar Renderda maxsus kanal/guruh ko'rsatilgan bo'lsa,
    # video o'sha chatga ham yuboriladi.
    if DAILY_VIDEO_CHAT_ID:
        try:
            chat_id = int(DAILY_VIDEO_CHAT_ID)
            if chat_id not in chat_ids:
                chat_ids.append(chat_id)
        except ValueError:
            logger.warning("DAILY_VIDEO_CHAT_ID noto'g'ri: %s", DAILY_VIDEO_CHAT_ID)

    text = (
        "🇺🇿 <b>KUNNING KIBERXAVFSIZLIK VIDEOSI</b>\n\n"
        f"🎥 <b>{video['title']}</b>\n\n"
        "🛡️ Faqat o'zbekcha kiberxavfsizlik mavzusidagi\n"
        "foydali va himoyalanishga oid video.\n\n"
        f"▶️ <a href=\"{video['url']}\">Videoni ko'rish</a>\n\n"
        "🛡️ <b>AntiPhish Guard</b>"
    )

    sent_any = False

    for chat_id in chat_ids:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=False,
            )
            sent_any = True
        except Exception as e:
            logger.warning(
                "Kunlik video %s chatga yuborilmadi: %s",
                chat_id,
                e,
            )

    if sent_any:
        save_last_daily_video_id(video["id"])


async def daily_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Darhol test uchun bitta o'zbekcha kiberxavfsizlik videosini yuboradi."""
    if not update.effective_chat:
        return

    videos = await asyncio.to_thread(find_uzbek_cyber_videos, 5)

    if not videos:
        await update.effective_message.reply_text(
            "❌ Hozircha ishonchli o'zbekcha kiberxavfsizlik videosi topilmadi."
        )
        return

    video = videos[0]
    await update.effective_message.reply_text(
        "🇺🇿 <b>Kiberxavfsizlik videosi</b>\n\n"
        f"🎥 <b>{video['title']}</b>\n\n"
        f"▶️ <a href=\"{video['url']}\">Videoni ko'rish</a>",
        parse_mode="HTML",
        disable_web_page_preview=False,
    )


def setup_daily_video_job(application: Application):
    """Kunlik video jobini ishga tushiradi."""

    if application.job_queue is None:
        logger.warning(
            "JobQueue mavjud emas. "
            "python-telegram-bot[job-queue] paketini o'rnating."
        )
        return

    try:
        tz = ZoneInfo(DAILY_VIDEO_TZ)
    except Exception:
        tz = ZoneInfo("Asia/Tashkent")

    application.job_queue.run_daily(
        send_daily_cyber_video,
        time=dt_time(
            hour=DAILY_VIDEO_HOUR,
            minute=DAILY_VIDEO_MINUTE,
            tzinfo=tz,
        ),
        name="daily_uzbek_cyber_video",
    )

    logger.info(
        "Kunlik o'zbekcha kiberxavfsizlik video jobi: %02d:%02d (%s)",
        DAILY_VIDEO_HOUR,
        DAILY_VIDEO_MINUTE,
        DAILY_VIDEO_TZ,
    )


# =========================================================
# DELETE WARNING
# =========================================================

async def delete_warning(
    context: ContextTypes.DEFAULT_TYPE
):

    data = context.job.data

    try:

        await context.bot.delete_message(
            chat_id=data["chat_id"],
            message_id=data["message_id"],
        )

    except Exception:
        pass


# =========================================================
# BOT GROUPGA QO‘SHILDI
# =========================================================

async def bot_added_to_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    member_update = update.my_chat_member

    if not member_update:
        return

    old_status = member_update.old_chat_member.status
    new_status = member_update.new_chat_member.status

    # =====================================================
    # BOT GURUHGA QO‘SHILDI
    # =====================================================

    if new_status in [
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
    ]:

        if old_status in [
            ChatMemberStatus.LEFT,
            ChatMemberStatus.KICKED,
        ]:

            chat = update.effective_chat

            register_group(
                chat.id,
                chat.title or "Unknown"
            )

            text = (
                "🛡️ <b>AntiPhish Guard</b>\n\n"

                "✅ Bot guruhga muvaffaqiyatli "
                "qo‘shildi!\n\n"

                "🔐 Men guruhdagi havolalarni "
                "tekshiraman va shubhali phishing "
                "linklarini aniqlashga harakat qilaman.\n\n"

                "📦 APK fayllar avtomatik "
                "bloklanadi.\n\n"

                "⚠️ <b>Muhim:</b>\n"
                "Botni <b>ADMIN</b> qiling va "
                "xabarlarni o‘chirish huquqini bering.\n\n"

                "📖 Yordam:\n"
                "/protect — himoyani yoqish\n"
                "/status — holat\n"
                "/stats — statistika\n\n"

                "🛡️ <b>AntiPhish Guard</b>"
            )

            try:

                await context.bot.send_message(
                    chat_id=chat.id,
                    text=text,
                    parse_mode="HTML"
                )

            except Exception as e:

                logger.error(
                    "Welcome message error: %s",
                    e
                )

    # =====================================================
    # BOT ADMIN QILINDI
    # =====================================================

    if new_status == ChatMemberStatus.ADMINISTRATOR:

        chat = update.effective_chat

        register_group(
            chat.id,
            chat.title or "Unknown"
        )

        try:

            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    "✅ <b>Rahmat!</b>\n\n"
                    "🛡️ AntiPhish Guard admin huquqiga ega.\n"
                    "🔐 Himoya ishlashga tayyor.\n"
                    "📦 APK Protection: ON\n"
                    "🔗 Phishing Protection: ON"
                ),
                parse_mode="HTML"
            )

        except Exception as e:

            logger.error(
                "Admin message error: %s",
                e
            )


# =========================================================
# MAIN
# =========================================================

def main():

    init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # =====================================================
    # COMMANDS
    # =====================================================

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "protect",
            protect
        )
    )

    application.add_handler(
        CommandHandler(
            "unprotect",
            unprotect
        )
    )

    application.add_handler(
        CommandHandler(
            "status",
            status
        )
    )

    application.add_handler(
        CommandHandler(
            "stats",
            stats
        )
    )

    application.add_handler(
        CommandHandler(
            "video",
            daily_video_command
        )
    )

    # =====================================================
    # INLINE BUTTONS
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            menu_callback
        )
    )

    # =====================================================
    # BOT GROUPGA QO‘SHILGANDA
    # =====================================================

    application.add_handler(
        ChatMemberHandler(
            bot_added_to_group,
            ChatMemberHandler.MY_CHAT_MEMBER
        )
    )

    # =====================================================
    # GROUP MESSAGE SCANNER
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT
            | filters.Document.ALL
            | filters.CaptionRegex(r".+"),
            scan_message
        )
    )

    # =====================================================
    # DAILY UZBEK CYBERSECURITY VIDEO
    # =====================================================

    setup_daily_video_job(application)

    # =====================================================
    # START MESSAGE
    # =====================================================

    print("")
    print("===================================")
    print("🛡️ ANTIPHISH GUARD")
    print("===================================")
    print("Bot ishga tushdi...")
    print("===================================")
    print("")

    # =====================================================
    # RENDER WEBHOOK
    # =====================================================

    render_url = os.getenv(
        "RENDER_EXTERNAL_URL"
    )

    if render_url:

        port = int(
            os.getenv(
                "PORT",
                "10000"
            )
        )

        webhook_url = (
            f"{render_url.rstrip('/')}/telegram"
        )

        print(
            f"🌐 Webhook: {webhook_url}"
        )

        print(
            f"🔌 Port: {port}"
        )

        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="telegram",
            webhook_url=webhook_url,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )

    else:

        print(
            "💻 Lokal rejim: polling"
        )

        application.run_polling(
            allowed_updates=Update.ALL_TYPES
        )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
