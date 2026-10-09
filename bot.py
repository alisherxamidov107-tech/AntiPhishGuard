import os
import re
import html
import json
import socket
import sqlite3
import logging
import asyncio
import urllib.parse
import urllib.request
from urllib.parse import urlparse
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
 
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
from i18n import (
    init_language_db,
    set_language,
    get_language,
    language_for_update,
    tr,
    language_keyboard,
    language_selection_text,
)
 
 
# =========================================================
# CONFIG
# =========================================================
 
load_dotenv()
 
BOT_TOKEN = os.getenv("BOT_TOKEN")
 
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. .env faylini tekshiring.")
 
 
# =========================================================
# LOGGING
# =========================================================
 
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
 
logger = logging.getLogger(__name__)
 
 
# =========================================================
# QO'SHIMCHA MATNLAR (i18n.py da yo'q kalitlar)
# =========================================================
 
EXTRA = {
    "uz": {
        "admin_only": "❌ Bu buyruq faqat adminlar uchun.",
        "home_text": (
            "🛡️ <b>AntiPhish Guard</b>\n\n"
            "🔐 Telegram guruhlaringizni phishing va shubhali "
            "havolalardan himoya qiluvchi xavfsizlik boti.\n\n"
            "⚡ <b>Asosiy imkoniyatlar:</b>\n"
            "• 🔗 Havolalarni tekshirish\n"
            "• 🚨 Phishingni aniqlash\n"
            "• 🗑️ Xavfli xabarlarni o‘chirish\n"
            "• 📦 APK fayllarni bloklash\n"
            "• 📊 Hodisalar statistikasi\n"
            "• ⚙️ Guruh himoyasini boshqarish\n"
            "• 🔎 Havolani botga yuboring va u haqida ma’lumot oling\n\n"
            "👇 Kerakli bo‘limni tanlang:"
        ),
        "guide_text": (
            "📖 <b>APG qo‘llanmasi</b>\n\n"
            "1️⃣ APG'ni guruhga qo‘shing.\n"
            "2️⃣ Botni administrator qiling.\n"
            "3️⃣ Xabarlarni o‘chirish huquqini bering.\n"
            "4️⃣ Group Privacy'ni o‘chirib qo‘ying.\n\n"
            "Shundan keyin APG guruhdagi xabarlarni tekshira oladi.\n\n"
            "🚨 Shubhali havola aniqlansa, xabar o‘chiriladi va "
            "guruhga ogohlantirish yuboriladi.\n\n"
            "📦 APK fayllar avtomatik bloklanadi."
        ),
        "protection_text": (
            "🛡️ <b>APG himoyasi</b>\n\n"
            "🔗 URL scanning — ON\n"
            "🚨 Phishing detection — ON\n"
            "📦 APK protection — ON\n"
            "🗑️ Xavfli xabarlarni o‘chirish — ON\n"
            "📊 Incident logging — ON\n\n"
            "Himoya guruh bo‘yicha alohida boshqariladi: "
            "/protect, /unprotect, /status"
        ),
        "stats_title": "📊 <b>APG statistikasi</b>\n\n🚨 Aniqlangan hodisalar: <b>{total}</b>",
        "stats_private": "📊 Statistikani ko‘rish uchun APG guruh ichida ishlashi kerak.",
        "protect_long": (
            "🛡️ <b>APG himoyasi yoqildi!</b>\n\n"
            "🔗 Havolalar tekshiriladi.\n"
            "🚨 Shubhali linklar aniqlanadi.\n"
            "📦 APK fayllar bloklanadi.\n"
            "🗑️ Xavfli xabarlar o‘chiriladi."
        ),
        "unprotect_long": "🔴 <b>APG himoyasi o‘chirildi.</b>",
        "status_on": "🟢 <b>APG faol</b>\n\n🛡️ Guruh himoyalangan.",
        "status_off": "🔴 <b>APG o‘chiq</b>\n\nHimoya vaqtincha o‘chirilgan.",
        "video_title": "🇺🇿 <b>KUNNING KIBERXAVFSIZLIK VIDEOSI</b>",
        "video_watch": "▶️ Videoni ko‘rish",
        "admin_only_lang": "❌ Tilni faqat adminlar o‘zgartira oladi.",
        "welcome_group": (
            "🛡️ <b>AntiPhish Guard</b>\n\n"
            "✅ Bot guruhga muvaffaqiyatli qo‘shildi!\n\n"
            "🔐 Men guruhdagi havolalarni tekshiraman va phishing "
            "linklarini aniqlashga harakat qilaman.\n\n"
            "📦 APK fayllar avtomatik bloklanadi.\n\n"
            "⚠️ <b>Muhim:</b>\n"
            "Botni <b>ADMIN</b> qiling va xabarlarni o‘chirish "
            "huquqini bering.\n\n"
            "/protect — himoyani yoqish\n"
            "/status — holat\n"
            "/stats — statistika\n"
            "/language — til\n\n"
            "🛡️ <b>AntiPhish Guard</b>"
        ),
        "thanks_admin": (
            "✅ <b>Rahmat!</b>\n\n"
            "🛡️ AntiPhish Guard admin huquqiga ega.\n"
            "🔐 Himoya ishlashga tayyor.\n"
            "📦 APK Protection: ON\n"
            "🔗 Phishing Protection: ON"
        ),
    },
    "ru": {
        "admin_only": "❌ Эта команда только для админов.",
        "home_text": (
            "🛡️ <b>AntiPhish Guard</b>\n\n"
            "🔐 Бот безопасности, защищающий ваши Telegram-группы от "
            "фишинга и подозрительных ссылок.\n\n"
            "⚡ <b>Возможности:</b>\n"
            "• 🔗 Проверка ссылок\n"
            "• 🚨 Обнаружение фишинга\n"
            "• 🗑️ Удаление опасных сообщений\n"
            "• 📦 Блокировка APK файлов\n"
            "• 📊 Статистика инцидентов\n"
            "• ⚙️ Управление защитой группы\n"
            "• 🔎 Отправьте ссылку боту и получите информацию о ней\n\n"
            "👇 Выберите раздел:"
        ),
        "guide_text": (
            "📖 <b>Инструкция APG</b>\n\n"
            "1️⃣ Добавьте APG в группу.\n"
            "2️⃣ Сделайте бота администратором.\n"
            "3️⃣ Дайте право удалять сообщения.\n"
            "4️⃣ Отключите Group Privacy.\n\n"
            "После этого APG сможет проверять сообщения группы.\n\n"
            "🚨 При обнаружении подозрительной ссылки сообщение "
            "удаляется, а в группу приходит предупреждение.\n\n"
            "📦 APK файлы блокируются автоматически."
        ),
        "protection_text": (
            "🛡️ <b>Защита APG</b>\n\n"
            "🔗 URL scanning — ON\n"
            "🚨 Phishing detection — ON\n"
            "📦 APK protection — ON\n"
            "🗑️ Удаление опасных сообщений — ON\n"
            "📊 Incident logging — ON\n\n"
            "Защита настраивается для каждой группы: "
            "/protect, /unprotect, /status"
        ),
        "stats_title": "📊 <b>Статистика APG</b>\n\n🚨 Обнаружено инцидентов: <b>{total}</b>",
        "stats_private": "📊 Для просмотра статистики APG должен работать в группе.",
        "protect_long": (
            "🛡️ <b>Защита APG включена!</b>\n\n"
            "🔗 Ссылки проверяются.\n"
            "🚨 Подозрительные ссылки обнаруживаются.\n"
            "📦 APK файлы блокируются.\n"
            "🗑️ Опасные сообщения удаляются."
        ),
        "unprotect_long": "🔴 <b>Защита APG выключена.</b>",
        "status_on": "🟢 <b>APG активен</b>\n\n🛡️ Группа защищена.",
        "status_off": "🔴 <b>APG выключен</b>\n\nЗащита временно отключена.",
        "video_title": "🇺🇿 <b>ВИДЕО ДНЯ ПО КИБЕРБЕЗОПАСНОСТИ</b>",
        "video_watch": "▶️ Смотреть видео",
        "admin_only_lang": "❌ Язык могут менять только админы.",
        "welcome_group": (
            "🛡️ <b>AntiPhish Guard</b>\n\n"
            "✅ Бот успешно добавлен в группу!\n\n"
            "🔐 Я проверяю ссылки в группе и стараюсь находить "
            "фишинговые.\n\n"
            "📦 APK файлы блокируются автоматически.\n\n"
            "⚠️ <b>Важно:</b>\n"
            "Сделайте бота <b>АДМИНОМ</b> и дайте право удалять "
            "сообщения.\n\n"
            "/protect — включить защиту\n"
            "/status — статус\n"
            "/stats — статистика\n"
            "/language — язык\n\n"
            "🛡️ <b>AntiPhish Guard</b>"
        ),
        "thanks_admin": (
            "✅ <b>Спасибо!</b>\n\n"
            "🛡️ У AntiPhish Guard есть права администратора.\n"
            "🔐 Защита готова к работе.\n"
            "📦 APK Protection: ON\n"
            "🔗 Phishing Protection: ON"
        ),
    },
    "en": {
        "admin_only": "❌ This command is for admins only.",
        "home_text": (
            "🛡️ <b>AntiPhish Guard</b>\n\n"
            "🔐 A security bot that protects your Telegram groups from "
            "phishing and suspicious links.\n\n"
            "⚡ <b>Features:</b>\n"
            "• 🔗 Link scanning\n"
            "• 🚨 Phishing detection\n"
            "• 🗑️ Deleting dangerous messages\n"
            "• 📦 APK file blocking\n"
            "• 📊 Incident statistics\n"
            "• ⚙️ Group protection control\n"
            "• 🔎 Send a link to the bot to get info about it\n\n"
            "👇 Choose a section:"
        ),
        "guide_text": (
            "📖 <b>APG Guide</b>\n\n"
            "1️⃣ Add APG to your group.\n"
            "2️⃣ Make the bot an administrator.\n"
            "3️⃣ Grant the right to delete messages.\n"
            "4️⃣ Disable Group Privacy.\n\n"
            "After that APG can scan group messages.\n\n"
            "🚨 If a suspicious link is found, the message is deleted "
            "and a warning is posted to the group.\n\n"
            "📦 APK files are blocked automatically."
        ),
        "protection_text": (
            "🛡️ <b>APG Protection</b>\n\n"
            "🔗 URL scanning — ON\n"
            "🚨 Phishing detection — ON\n"
            "📦 APK protection — ON\n"
            "🗑️ Dangerous message deletion — ON\n"
            "📊 Incident logging — ON\n\n"
            "Protection is managed per group: "
            "/protect, /unprotect, /status"
        ),
        "stats_title": "📊 <b>APG statistics</b>\n\n🚨 Incidents detected: <b>{total}</b>",
        "stats_private": "📊 APG must be working inside a group to show statistics.",
        "protect_long": (
            "🛡️ <b>APG protection enabled!</b>\n\n"
            "🔗 Links will be scanned.\n"
            "🚨 Suspicious links will be detected.\n"
            "📦 APK files will be blocked.\n"
            "🗑️ Dangerous messages will be deleted."
        ),
        "unprotect_long": "🔴 <b>APG protection disabled.</b>",
        "status_on": "🟢 <b>APG is active</b>\n\n🛡️ The group is protected.",
        "status_off": "🔴 <b>APG is off</b>\n\nProtection is temporarily disabled.",
        "video_title": "🇺🇿 <b>CYBERSECURITY VIDEO OF THE DAY</b>",
        "video_watch": "▶️ Watch video",
        "admin_only_lang": "❌ Only admins can change the language.",
        "welcome_group": (
            "🛡️ <b>AntiPhish Guard</b>\n\n"
            "✅ The bot was added to the group!\n\n"
            "🔐 I scan links in the group and try to detect phishing.\n\n"
            "📦 APK files are blocked automatically.\n\n"
            "⚠️ <b>Important:</b>\n"
            "Make the bot an <b>ADMIN</b> and grant the right to delete "
            "messages.\n\n"
            "/protect — enable protection\n"
            "/status — status\n"
            "/stats — statistics\n"
            "/language — language\n\n"
            "🛡️ <b>AntiPhish Guard</b>"
        ),
        "thanks_admin": (
            "✅ <b>Thank you!</b>\n\n"
            "🛡️ AntiPhish Guard has admin rights.\n"
            "🔐 Protection is ready.\n"
            "📦 APK Protection: ON\n"
            "🔗 Phishing Protection: ON"
        ),
    },
}
 
 
def t(lang: str, key: str, **kwargs) -> str:
    """Avval EXTRA, topilmasa i18n.tr dan matn oladi."""
    table = EXTRA.get(lang, EXTRA["uz"])
 
    if key in table or key in EXTRA["uz"]:
        text = table.get(key) or EXTRA["uz"][key]
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text
 
    return tr(lang, key, **kwargs)
 
 
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
    """, (chat_id, title, datetime.now().isoformat()))
    conn.commit()
    conn.close()
 
 
def is_protection_enabled(chat_id: int) -> bool:
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT enabled FROM groups WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
 
    if result is None:
        return True
 
    return bool(result[0])
 
 
def set_protection(chat_id: int, enabled: bool):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE groups SET enabled = ? WHERE chat_id = ?",
        (1 if enabled else 0, chat_id),
    )
    conn.commit()
    conn.close()
 
 
def save_incident(chat_id: int, user_id: int, username: str, url: str):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO incidents
        (chat_id, user_id, username, url, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (chat_id, user_id, username, url, datetime.now().isoformat()))
    conn.commit()
    conn.close()
 
 
def get_stats(chat_id: int) -> int:
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM incidents WHERE chat_id = ?",
        (chat_id,),
    )
    total = cursor.fetchone()[0]
    conn.close()
    return total
 
 
# =========================================================
# ADMIN CHECK
# =========================================================
 
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.effective_chat or not update.effective_user:
        return False
 
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id,
        )
 
        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )
 
    except Exception as e:
        logger.error("Admin tekshirish xatosi: %s", e)
        return False
 
 
# =========================================================
# MENYU
# =========================================================
 
async def main_keyboard(context: ContextTypes.DEFAULT_TYPE, lang: str):
    bot = await context.bot.get_me()
    add_url = f"https://t.me/{bot.username}?startgroup=true"
 
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(lang, "add_group"), url=add_url)],
        [
            InlineKeyboardButton(tr(lang, "guide"), callback_data="guide"),
            InlineKeyboardButton(tr(lang, "protection"), callback_data="protection"),
        ],
        [InlineKeyboardButton(tr(lang, "statistics"), callback_data="statistics")],
        [InlineKeyboardButton(tr(lang, "language_menu"), callback_data="language")],
    ])
 
 
def back_keyboard(lang: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(lang, "back"), callback_data="home")]
    ])
 
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message:
        return
 
    lang = language_for_update(update)
 
    await message.reply_text(
        t(lang, "home_text"),
        parse_mode="HTML",
        reply_markup=await main_keyboard(context, lang),
    )
 
 
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
 
    lang = language_for_update(update)
 
    if query.data == "guide":
        await query.edit_message_text(
            t(lang, "guide_text"),
            parse_mode="HTML",
            reply_markup=back_keyboard(lang),
        )
 
    elif query.data == "protection":
        await query.edit_message_text(
            t(lang, "protection_text"),
            parse_mode="HTML",
            reply_markup=back_keyboard(lang),
        )
 
    elif query.data == "statistics":
        chat = query.message.chat if query.message else None
 
        if chat and chat.type in ("group", "supergroup"):
            text = t(lang, "stats_title", total=get_stats(chat.id))
        else:
            text = t(lang, "stats_private")
 
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=back_keyboard(lang),
        )
 
    elif query.data == "home":
        await query.edit_message_text(
            t(lang, "home_text"),
            parse_mode="HTML",
            reply_markup=await main_keyboard(context, lang),
        )
 
 
# =========================================================
# TIL
# =========================================================
 
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message:
        return
 
    await message.reply_text(
        language_selection_text(),
        parse_mode="HTML",
        reply_markup=language_keyboard(),
    )
 
 
async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
 
    if data == "language":
        await query.answer()
        await query.edit_message_text(
            language_selection_text(),
            parse_mode="HTML",
            reply_markup=language_keyboard(),
        )
        return
 
    if data.startswith("setlang:"):
        lang = data.split(":", 1)[1]
        if lang not in ("uz", "ru", "en"):
            lang = "uz"
 
        chat = query.message.chat if query.message else None
        user = query.from_user
 
        if chat and chat.type in ("group", "supergroup"):
            # Guruh tilini faqat adminlar o'zgartiradi.
            if not await is_admin(update, context):
                await query.answer(
                    t(get_language("chat", chat.id), "admin_only_lang"),
                    show_alert=True,
                )
                return
            set_language("chat", chat.id, lang)
        elif user:
            set_language("user", user.id, lang)
 
        await query.answer()
        await query.edit_message_text(
            tr(lang, "language_saved") + "\n\n" + tr(lang, "start_choose"),
            parse_mode="HTML",
        )
 
 
# =========================================================
# PROTECT / UNPROTECT / STATUS / STATS
# =========================================================
 
async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
 
    if not chat or not message:
        return
 
    lang = language_for_update(update)
 
    if chat.type not in ("group", "supergroup"):
        await message.reply_text(tr(lang, "group_only"))
        return
 
    if not await is_admin(update, context):
        await message.reply_text(t(lang, "admin_only"))
        return
 
    register_group(chat.id, chat.title or "Unknown")
    set_protection(chat.id, True)
 
    await message.reply_text(t(lang, "protect_long"), parse_mode="HTML")
 
 
async def unprotect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
 
    if not chat or not message:
        return
 
    lang = language_for_update(update)
 
    if chat.type not in ("group", "supergroup"):
        await message.reply_text(tr(lang, "group_only"))
        return
 
    if not await is_admin(update, context):
        await message.reply_text(t(lang, "admin_only"))
        return
 
    register_group(chat.id, chat.title or "Unknown")
    set_protection(chat.id, False)
 
    await message.reply_text(t(lang, "unprotect_long"), parse_mode="HTML")
 
 
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
 
    if not chat or not message:
        return
 
    lang = language_for_update(update)
 
    if chat.type not in ("group", "supergroup"):
        await message.reply_text(tr(lang, "group_only"))
        return
 
    key = "status_on" if is_protection_enabled(chat.id) else "status_off"
    await message.reply_text(t(lang, key), parse_mode="HTML")
 
 
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
 
    if not chat or not message:
        return
 
    lang = language_for_update(update)
    total = get_stats(chat.id)
 
    await message.reply_text(
        t(lang, "stats_title", total=total),
        parse_mode="HTML",
    )
 
 
# =========================================================
# LINK IP / LOCATION LOOKUP
# =========================================================
 
def get_link_info(url: str):
    """
    Domenning DNS orqali server IP manzilini aniqlaydi.
    IP geolocation server IP bo'yicha taxminiy davlat/shahar/ISP beradi.
    Bu linkni yuborgan odamning IP manzili emas.
    Bloklovchi funksiya: asyncio.to_thread orqali chaqiring.
    """
    try:
        clean_url = (url or "").rstrip(".,!?;:)")
 
        if not clean_url.lower().startswith(("http://", "https://")):
            clean_url = "https://" + clean_url
 
        parsed = urlparse(clean_url)
        domain = parsed.hostname
 
        if not domain:
            return None
 
        domain = domain.lower()
        ip = socket.gethostbyname(domain)
 
        country = "?"
        city = "?"
        isp = "?"
 
        try:
            request = urllib.request.Request(
                f"https://ipwho.is/{ip}",
                headers={"User-Agent": "AntiPhishGuard/1.0"},
            )
 
            with urllib.request.urlopen(request, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
 
            if data.get("success") is True:
                connection = data.get("connection") or {}
                country = data.get("country") or "?"
                city = data.get("city") or "?"
                isp = connection.get("isp") or connection.get("org") or "?"
 
        except Exception as e:
            logger.warning("IP geolocation xatosi: %s", e)
 
        return {
            "domain": domain,
            "ip": ip,
            "country": country,
            "city": city,
            "isp": isp,
        }
 
    except Exception as e:
        logger.warning("Link IP aniqlash xatosi: %s", e)
        return None
 
 
async def build_link_block(url: str, lang: str, with_title: bool = False) -> str:
    """Link haqida server IP/joylashuv bloki (HTML)."""
    info = await asyncio.to_thread(get_link_info, url)
    unknown = tr(lang, "not_found")
 
    def val(x):
        return html.escape(unknown if x in (None, "", "?") else str(x))
 
    lines = []
 
    if with_title:
        lines += [tr(lang, "link_analysis"), ""]
 
    lines.append(f"{tr(lang, 'link')}: <code>{html.escape(url)}</code>")
 
    if info:
        lines += [
            f"{tr(lang, 'domain')}: <code>{html.escape(info['domain'])}</code>",
            f"{tr(lang, 'server_ip')}: <code>{html.escape(info['ip'])}</code>",
            f"{tr(lang, 'country')}: {val(info['country'])}",
            f"{tr(lang, 'city')}: {val(info['city'])}",
            f"{tr(lang, 'isp')}: {val(info['isp'])}",
        ]
    else:
        lines.append(tr(lang, "ip_failed"))
 
    return "\n".join(lines)
 
 
# =========================================================
# MESSAGE SCANNER
# =========================================================
 
def is_apk_document(document) -> bool:
    if not document:
        return False
 
    file_name = (document.file_name or "").lower()
    mime_type = (document.mime_type or "").lower()
 
    return (
        file_name.endswith(".apk")
        or mime_type == "application/vnd.android.package-archive"
    )
 
 
async def scan_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
 
    if not message or not chat:
        return
 
    is_private = chat.type == "private"
    is_group = chat.type in ("group", "supergroup")
 
    if not (is_private or is_group):
        return
 
    # Guruhda himoya o'chirilgan bo'lsa tekshirmaymiz.
    if is_group and not is_protection_enabled(chat.id):
        return
 
    user = update.effective_user
    lang = language_for_update(update)
    username = user.mention_html() if user else "User"
    username_db = user.username if user and user.username else ""
    user_id = user.id if user else 0
 
    # =====================================================
    # 1) HAMMA APK FAYLLARNI O'CHIRISH
    # =====================================================
    if is_apk_document(message.document):
        try:
            await message.delete()
        except Exception as e:
            logger.warning("APK xabarini o'chirib bo'lmadi: %s", e)
 
        try:
            scanning = await context.bot.send_message(
                chat_id=chat.id,
                text=tr(lang, "apk_title"),
                parse_mode="HTML",
            )
            await asyncio.sleep(0.7)
            await scanning.edit_text(
                tr(lang, "apk_blocked", user=username),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("APK ogohlantirishida xato: %s", e)
 
        return
 
    # =====================================================
    # 2) LINKLARNI TAHLIL QILISH
    # =====================================================
    text = message.text or message.caption or ""
    if not text:
        return
 
    urls = extract_urls(text)
    if not urls:
        return
 
    dangerous_urls = scan_text(text)
 
    # ---------- Shaxsiy chat (botga yuborilgan) ----------
    if is_private:
        blocks = []
 
        for url in urls:
            block = await build_link_block(url, lang, with_title=True)
            verdict = (
                tr(lang, "verdict_danger")
                if url in dangerous_urls
                else tr(lang, "verdict_safe")
            )
            blocks.append(f"{block}\n\n{verdict}\n{tr(lang, 'approx_location')}")
 
        result_text = "\n\n".join(blocks)
 
        if dangerous_urls:
            for url in dangerous_urls:
                save_incident(chat.id, user_id, username_db, url)
 
            try:
                await message.delete()
            except Exception as e:
                logger.warning("Shaxsiy chatda o'chirib bo'lmadi: %s", e)
 
            await context.bot.send_message(
                chat_id=chat.id,
                text=result_text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        else:
            await message.reply_text(
                result_text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
 
        return
 
    # ---------- Guruh ----------
    if not dangerous_urls:
        return
 
    blocks = [await build_link_block(url, lang) for url in dangerous_urls]
 
    for url in dangerous_urls:
        save_incident(chat.id, user_id, username_db, url)
 
    try:
        await message.delete()
    except Exception as e:
        logger.warning("Xabarni o'chirib bo'lmadi: %s", e)
 
    try:
        scanning = await context.bot.send_message(
            chat_id=chat.id,
            text=tr(lang, "scan_title"),
            parse_mode="HTML",
        )
        await asyncio.sleep(0.7)
        await scanning.edit_text(
            tr(
                lang,
                "phishing_blocked",
                user=username,
                details="\n\n".join(blocks),
            ),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error("Warning yuborishda xato: %s", e)
 
 
# =========================================================
# KUNLIK O'ZBEKCHA KIBERXAVFSIZLIK VIDEOSI
# =========================================================
 
DAILY_VIDEO_CHAT_ID = os.getenv("DAILY_VIDEO_CHAT_ID")
DAILY_VIDEO_HOUR = int(os.getenv("DAILY_VIDEO_HOUR", "12"))
DAILY_VIDEO_MINUTE = int(os.getenv("DAILY_VIDEO_MINUTE", "0"))
DAILY_VIDEO_TZ = os.getenv("DAILY_VIDEO_TZ", "Asia/Tashkent")
 
VIDEO_SEARCH_QUERIES = [
    "Kiberxavfsizlik markazi kiberxavfsizlik",
    "Kiberxavfsizlik markazi firibgarlik",
    "Kiberxavfsizlik markazi himoya",
    "ICHKI ISHLAR VAZIRLIGI kiberxavfsizlik",
]
 
UZBEK_CYBER_WORDS = [
    "kiber", "xavfsizlik", "firibgarlik", "himoya", "parol",
    "shaxsiy", "ma'lumot", "ma’lumot", "zararli", "virus",
    "phishing", "apk", "ogoh", "firibgar", "akkaunt", "internet",
]
 
UZBEK_MARKERS = [
    "o'zbek", "o‘zbek", "uzbek", "xavfsizlik",
    "firibgarlik", "himoya", "parol", "ma'lumot",
    "ma’lumot", "zararli", "ogoh", "firibgar",
]
 
TRUSTED_VIDEO_CHANNEL_HINTS = [
    "Kiberxavfsizlik markazi",
    "ICHKI ISHLAR VAZIRLIGI",
    "csecuz",
    "ichkiishlarvazirligi",
]
 
 
def find_uzbek_cyber_videos(limit: int = 5):
    """
    YouTube public search sahifasidan kiberxavfsizlikka oid
    o'zbekcha videolarni topishga harakat qiladi.
    Faqat havola yuboriladi, video yuklab olinmaydi.
    """
    found = []
    seen = set()
 
    for query in VIDEO_SEARCH_QUERIES:
        try:
            search_url = (
                "https://www.youtube.com/results?search_query="
                + urllib.parse.quote_plus(query)
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
 
            ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', page)
 
            for video_id in ids:
                if video_id in seen:
                    continue
 
                pos = page.find('"videoId":"' + video_id + '"')
                chunk = page[max(0, pos - 2500):pos + 5000]
 
                title_match = re.search(
                    r'"title":\{"runs":\[\{"text":"(.*?)"', chunk, re.S
                )
                owner_match = re.search(
                    r'"ownerText":\{"runs":\[\{"text":"(.*?)"', chunk, re.S
                )
 
                title = (
                    html.unescape(title_match.group(1))
                    if title_match
                    else "Kiberxavfsizlik videosi"
                )
                owner = (
                    html.unescape(owner_match.group(1))
                    if owner_match
                    else ""
                )
 
                title_lower = title.lower()
                owner_lower = owner.lower()
 
                if not any(w in title_lower for w in UZBEK_CYBER_WORDS):
                    continue
 
                if not any(m in title_lower for m in UZBEK_MARKERS):
                    continue
 
                if not any(
                    h.lower() in owner_lower
                    for h in TRUSTED_VIDEO_CHANNEL_HINTS
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
            logger.warning("YouTube qidiruv xatosi (%s): %s", query, e)
 
    return found
 
 
def get_last_daily_video_id():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT last_video_id FROM daily_video_state WHERE id = 1")
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
 
 
def video_message_text(lang: str, video: dict, with_footer: bool = True) -> str:
    text = (
        f"{t(lang, 'video_title')}\n\n"
        f"🎥 <b>{html.escape(video['title'])}</b>\n\n"
        f"<a href=\"{html.escape(video['url'])}\">{t(lang, 'video_watch')}</a>"
    )
 
    if with_footer:
        text += "\n\n🛡️ <b>AntiPhish Guard</b>"
 
    return text
 
 
async def send_daily_cyber_video(context: ContextTypes.DEFAULT_TYPE):
    """Har kuni bir marta ro'yxatdan o'tgan guruhlarga video havolasini yuboradi."""
 
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
 
    if DAILY_VIDEO_CHAT_ID:
        try:
            extra_id = int(DAILY_VIDEO_CHAT_ID)
            if extra_id not in chat_ids:
                chat_ids.append(extra_id)
        except ValueError:
            logger.warning("DAILY_VIDEO_CHAT_ID noto'g'ri: %s", DAILY_VIDEO_CHAT_ID)
 
    sent_any = False
 
    for chat_id in chat_ids:
        try:
            lang = get_language("chat", chat_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=video_message_text(lang, video),
                parse_mode="HTML",
                disable_web_page_preview=False,
            )
            sent_any = True
        except Exception as e:
            logger.warning("Kunlik video %s chatga yuborilmadi: %s", chat_id, e)
 
    if sent_any:
        save_last_daily_video_id(video["id"])
 
 
async def daily_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Darhol test uchun bitta videoni yuboradi."""
    message = update.effective_message
 
    if not update.effective_chat or not message:
        return
 
    lang = language_for_update(update)
    videos = await asyncio.to_thread(find_uzbek_cyber_videos, 5)
 
    if not videos:
        await message.reply_text(tr(lang, "no_video"))
        return
 
    await message.reply_text(
        video_message_text(lang, videos[0], with_footer=False),
        parse_mode="HTML",
        disable_web_page_preview=False,
    )
 
 
def setup_daily_video_job(application: Application):
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
        "Kunlik video jobi: %02d:%02d (%s)",
        DAILY_VIDEO_HOUR,
        DAILY_VIDEO_MINUTE,
        DAILY_VIDEO_TZ,
    )
 
 
# =========================================================
# BOT GURUHGA QO'SHILDI / ADMIN QILINDI
# =========================================================
 
async def bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member_update = update.my_chat_member
 
    if not member_update:
        return
 
    chat = update.effective_chat
 
    if not chat or chat.type not in ("group", "supergroup"):
        return
 
    old_status = member_update.old_chat_member.status
    new_status = member_update.new_chat_member.status
    lang = get_language("chat", chat.id)
 
    # Bot guruhga qo'shildi.
    if (
        new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR)
        and old_status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)
    ):
        register_group(chat.id, chat.title or "Unknown")
 
        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=t(lang, "welcome_group"),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error("Welcome message error: %s", e)
 
    # Bot admin qilindi (oldin admin bo'lmagan bo'lsa).
    if (
        new_status == ChatMemberStatus.ADMINISTRATOR
        and old_status != ChatMemberStatus.ADMINISTRATOR
    ):
        register_group(chat.id, chat.title or "Unknown")
 
        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=t(lang, "thanks_admin"),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error("Admin message error: %s", e)
 
 
# =========================================================
# GLOBAL XATO HANDLERI
# =========================================================
 
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Kutilmagan xato:", exc_info=context.error)
 
 
# =========================================================
# MAIN
# =========================================================
 
def main():
    init_db()
    init_language_db()
 
    application = Application.builder().token(BOT_TOKEN).build()
 
    # Komandalar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("protect", protect))
    application.add_handler(CommandHandler("unprotect", unprotect))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("video", daily_video_command))
    application.add_handler(CommandHandler("language", language_command))
 
    # Inline tugmalar (til handleri OLDIN turishi shart)
    application.add_handler(
        CallbackQueryHandler(
            language_callback,
            pattern=r"^(language|setlang:(uz|ru|en))$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            menu_callback,
            pattern=r"^(guide|protection|statistics|home)$",
        )
    )
 
    # Bot guruhga qo'shilganda
    application.add_handler(
        ChatMemberHandler(
            bot_added_to_group,
            ChatMemberHandler.MY_CHAT_MEMBER,
        )
    )
 
    # Xabarlarni tekshirish (guruh + shaxsiy chat)
    application.add_handler(
        MessageHandler(
            (filters.TEXT | filters.Document.ALL | filters.CaptionRegex(r".+"))
            & ~filters.COMMAND,
            scan_message,
        )
    )
 
    application.add_error_handler(error_handler)
 
    setup_daily_video_job(application)
 
    print("")
    print("===================================")
    print("🛡️ ANTIPHISH GUARD")
    print("===================================")
    print("Bot ishga tushdi...")
    print("===================================")
    print("")
 
    render_url = os.getenv("RENDER_EXTERNAL_URL")
 
    if render_url:
        port = int(os.getenv("PORT", "10000"))
        webhook_url = f"{render_url.rstrip('/')}/telegram"
 
        print(f"🌐 Webhook: {webhook_url}")
        print(f"🔌 Port: {port}")
 
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="telegram",
            webhook_url=webhook_url,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
    else:
        print("💻 Lokal rejim: polling")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
 
 
if __name__ == "__main__":
    main()
