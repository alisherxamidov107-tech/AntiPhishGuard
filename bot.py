import os
import re
import hmac
import html
import json
import time
import random
import socket
import sqlite3
import logging
import asyncio
import ipaddress
import urllib.parse
import urllib.request
from contextlib import contextmanager
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
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ChatMemberHandler,
    CallbackQueryHandler,
    BusinessConnectionHandler,
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

DB_NAME = os.getenv("DB_PATH", "database.db")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
try:
    OWNER_TELEGRAM_ID = int(os.getenv("OWNER_TELEGRAM_ID", "0"))
except (TypeError, ValueError):
    OWNER_TELEGRAM_ID = 0

ADMIN_SESSION_SECONDS = 3600
ADMIN_MAX_FAILS = 5
ADMIN_FAIL_WINDOW = 900

DAILY_VIDEO_CHAT_ID = os.getenv("DAILY_VIDEO_CHAT_ID")
DAILY_VIDEO_HOUR = int(os.getenv("DAILY_VIDEO_HOUR", "19"))
DAILY_VIDEO_MINUTE = int(os.getenv("DAILY_VIDEO_MINUTE", "0"))
DAILY_VIDEO_TZ = os.getenv("DAILY_VIDEO_TZ", "Asia/Tashkent")

SUPPORTED_LANGS = ("uz", "ru", "en")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# =========================================================
# MATNLAR
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
            "• 🎬 Kunlik kiberxavfsizlik videosi (/video)\n"
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
        "video_title": "🎬 <b>KIBERJINOYATGA QARSHI: KUN VIDEOSI</b>",
        "video_watch": "▶️ Videoni ko‘rish",
        "admin_only_lang": "❌ Tilni faqat adminlar o‘zgartira oladi.",
        "geo_note": "ℹ️ Bu server IP manzilining taxminiy geolokatsiyasi; havolani yuborgan odamning joylashuvi emas.",
        "cant_delete": (
            "⚠️ Xavfli xabarni o‘chira olmadim. Botni admin qiling va "
            "«Xabarlarni o‘chirish» huquqini bering."
        ),
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
            "/video — kiberxavfsizlik videosi\n"
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
            "• 🎬 Ежедневное видео по кибербезопасности (/video)\n"
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
        "video_title": "🎬 <b>ВИДЕО ДНЯ: ПРОТИВ КИБЕРПРЕСТУПНОСТИ</b>",
        "video_watch": "▶️ Смотреть видео",
        "admin_only_lang": "❌ Язык могут менять только админы.",
        "geo_note": "ℹ️ Это примерная геолокация IP-адреса сервера, а не местоположение отправителя ссылки.",
        "cant_delete": (
            "⚠️ Не удалось удалить опасное сообщение. Сделайте бота "
            "админом и дайте право «Удаление сообщений»."
        ),
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
            "/video — видео по кибербезопасности\n"
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
            "• 🎬 Daily cybersecurity video (/video)\n"
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
        "video_title": "🎬 <b>VIDEO OF THE DAY: FIGHTING CYBERCRIME</b>",
        "video_watch": "▶️ Watch video",
        "admin_only_lang": "❌ Only admins can change the language.",
        "geo_note": "ℹ️ This is an approximate geolocation of the server IP, not the location of the person who sent the link.",
        "cant_delete": (
            "⚠️ I could not delete the dangerous message. Make the bot "
            "an admin and grant the «Delete messages» right."
        ),
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
            "/video — cybersecurity video\n"
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

BIZ_TEXTS = {
    "uz": {
        "biz_connected": (
            "✅ <b>AntiPhish Guard Business chatlaringizga ulandi.</b>\n\n"
            "Boshqalardan kelgan APK fayllar va phishing havolali xabarlar "
            "shaxsiy chatlaringizda avtomatik o‘chiriladi.\n\n"
            "🔒 Ogohlantirishlar faqat shu yerda sizga yuboriladi, "
            "suhbatdoshlaringiz hech narsa ko‘rmaydi."
        ),
        "biz_no_delete": (
            "⚠️ Botda xabarlarni o‘chirish ruxsati yo‘q.\n"
            "Settings → Business → Chatbots bo‘limida xabarlarni "
            "boshqarish (o‘chirish) ruxsatini yoqing."
        ),
        "biz_disconnected": "🔕 Business ulanish o‘chirildi.",
        "biz_apk": (
            "🚨 <b>Business chat: APK bloklandi</b>\n\n"
            "👤 Yuboruvchi: {sender}\n"
            "💬 Chat: {chat}\n"
            "📦 Android APK fayl yuborilgan edi."
        ),
        "biz_phish": (
            "🚨 <b>Business chat: phishing havola bloklandi</b>\n\n"
            "👤 Yuboruvchi: {sender}\n"
            "💬 Chat: {chat}\n\n"
            "{details}\n\n"
            "🚫 Bu havolaga kirmang!"
        ),
        "biz_deleted": "🗑️ Xabar o‘chirildi.",
        "biz_not_deleted": (
            "⚠️ Xabarni o‘chirib bo‘lmadi. Botga Business sozlamalarida "
            "xabarlarni o‘chirish ruxsatini bering."
        ),
    },
    "ru": {
        "biz_connected": (
            "✅ <b>AntiPhish Guard подключён к вашим Business-чатам.</b>\n\n"
            "APK файлы и сообщения с фишинговыми ссылками от других "
            "людей будут автоматически удаляться в ваших личных чатах.\n\n"
            "🔒 Предупреждения приходят только вам сюда, собеседники "
            "ничего не увидят."
        ),
        "biz_no_delete": (
            "⚠️ У бота нет права удалять сообщения.\n"
            "Включите право управления сообщениями в "
            "Settings → Business → Chatbots."
        ),
        "biz_disconnected": "🔕 Business-подключение отключено.",
        "biz_apk": (
            "🚨 <b>Business-чат: APK заблокирован</b>\n\n"
            "👤 Отправитель: {sender}\n"
            "💬 Чат: {chat}\n"
            "📦 Был отправлен Android APK файл."
        ),
        "biz_phish": (
            "🚨 <b>Business-чат: фишинговая ссылка заблокирована</b>\n\n"
            "👤 Отправитель: {sender}\n"
            "💬 Чат: {chat}\n\n"
            "{details}\n\n"
            "🚫 Не переходите по этой ссылке!"
        ),
        "biz_deleted": "🗑️ Сообщение удалено.",
        "biz_not_deleted": (
            "⚠️ Не удалось удалить сообщение. Дайте боту право удалять "
            "сообщения в настройках Business."
        ),
    },
    "en": {
        "biz_connected": (
            "✅ <b>AntiPhish Guard is connected to your Business chats.</b>\n\n"
            "APK files and phishing links sent to you by others will be "
            "deleted automatically in your private chats.\n\n"
            "🔒 Alerts are sent only to you here; the people you chat "
            "with see nothing."
        ),
        "biz_no_delete": (
            "⚠️ The bot has no permission to delete messages.\n"
            "Enable message management in Settings → Business → Chatbots."
        ),
        "biz_disconnected": "🔕 Business connection removed.",
        "biz_apk": (
            "🚨 <b>Business chat: APK blocked</b>\n\n"
            "👤 Sender: {sender}\n"
            "💬 Chat: {chat}\n"
            "📦 An Android APK file was sent."
        ),
        "biz_phish": (
            "🚨 <b>Business chat: phishing link blocked</b>\n\n"
            "👤 Sender: {sender}\n"
            "💬 Chat: {chat}\n\n"
            "{details}\n\n"
            "🚫 Do not open this link!"
        ),
        "biz_deleted": "🗑️ Message deleted.",
        "biz_not_deleted": (
            "⚠️ Could not delete the message. Grant the bot permission to "
            "delete messages in Business settings."
        ),
    },
}

for _lang, _texts in BIZ_TEXTS.items():
    EXTRA[_lang].update(_texts)


def norm_lang(lang) -> str:
    return lang if lang in SUPPORTED_LANGS else "uz"


def t(lang: str, key: str, **kwargs) -> str:
    """Avval EXTRA, topilmasa i18n.tr dan matn oladi."""
    lang = norm_lang(lang)
    table = EXTRA[lang]

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

@contextmanager
def db():
    conn = sqlite3.connect(DB_NAME, timeout=15)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)
        # Eski bazalar uchun migratsiya: bot chiqarib yuborilgan guruhlarni belgilash.
        try:
            cur.execute("ALTER TABLE groups ADD COLUMN active INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass

        cur.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                username TEXT,
                url TEXT,
                created_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_video_by_lang (
                lang TEXT PRIMARY KEY,
                last_video_id TEXT,
                updated_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS business_connections (
                connection_id TEXT PRIMARY KEY,
                user_id INTEGER,
                user_chat_id INTEGER,
                is_enabled INTEGER DEFAULT 1,
                can_delete INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                active INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)


def save_business_connection(bc):
    rights = getattr(bc, "rights", None)
    can_delete = (
        bool(getattr(rights, "can_delete_all_messages", False))
        if rights is not None
        else True
    )

    with db() as conn:
        conn.execute("""
            INSERT INTO business_connections
            (connection_id, user_id, user_chat_id, is_enabled, can_delete, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(connection_id) DO UPDATE SET
                user_id = excluded.user_id,
                user_chat_id = excluded.user_chat_id,
                is_enabled = excluded.is_enabled,
                can_delete = excluded.can_delete
        """, (
            bc.id,
            bc.user.id,
            bc.user_chat_id,
            1 if bc.is_enabled else 0,
            1 if can_delete else 0,
            datetime.now().isoformat(),
        ))


def get_business_connection(connection_id: str):
    with db() as conn:
        row = conn.execute("""
            SELECT user_id, user_chat_id, is_enabled, can_delete
            FROM business_connections WHERE connection_id = ?
        """, (connection_id,)).fetchone()

    if not row:
        return None

    return {
        "user_id": row[0],
        "user_chat_id": row[1],
        "is_enabled": bool(row[2]),
        "can_delete": bool(row[3]),
    }


def register_group(chat_id: int, title: str):
    with db() as conn:
        conn.execute("""
            INSERT INTO groups (chat_id, title, enabled, created_at, active)
            VALUES (?, ?, 1, ?, 1)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                active = 1
        """, (chat_id, title, datetime.now().isoformat()))


def mark_group_inactive(chat_id: int):
    with db() as conn:
        conn.execute("UPDATE groups SET active = 0 WHERE chat_id = ?", (chat_id,))


def register_user(user_id: int):
    with db() as conn:
        conn.execute("""
            INSERT INTO users (user_id, active, created_at) VALUES (?, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET active = 1
        """, (user_id, datetime.now().isoformat()))


def mark_user_inactive(user_id: int):
    with db() as conn:
        conn.execute("UPDATE users SET active = 0 WHERE user_id = ?", (user_id,))


def is_protection_enabled(chat_id: int) -> bool:
    with db() as conn:
        row = conn.execute(
            "SELECT enabled FROM groups WHERE chat_id = ?", (chat_id,)
        ).fetchone()

    if row is None:
        return True
    return bool(row[0])


def set_protection(chat_id: int, enabled: bool):
    with db() as conn:
        conn.execute(
            "UPDATE groups SET enabled = ? WHERE chat_id = ?",
            (1 if enabled else 0, chat_id),
        )


def save_incident(chat_id: int, user_id: int, username: str, url: str):
    with db() as conn:
        conn.execute("""
            INSERT INTO incidents (chat_id, user_id, username, url, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, user_id, username, url, datetime.now().isoformat()))


def get_stats(chat_id: int) -> int:
    with db() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM incidents WHERE chat_id = ?", (chat_id,)
        ).fetchone()[0]


# =========================================================
# ADMIN CHECK (guruh adminlari)
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

    chat = update.effective_chat

    if chat and chat.type == "private":
        if update.effective_user:
            register_user(update.effective_user.id)
        await message.reply_text(
            language_selection_text(),
            parse_mode="HTML",
            reply_markup=language_keyboard(),
        )
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
            t(lang, "guide_text"), parse_mode="HTML",
            reply_markup=back_keyboard(lang),
        )

    elif query.data == "protection":
        await query.edit_message_text(
            t(lang, "protection_text"), parse_mode="HTML",
            reply_markup=back_keyboard(lang),
        )

    elif query.data == "statistics":
        chat = query.message.chat if query.message else None

        if chat and chat.type in ("group", "supergroup"):
            text = t(lang, "stats_title", total=get_stats(chat.id))
        else:
            text = t(lang, "stats_private")

        await query.edit_message_text(
            text, parse_mode="HTML", reply_markup=back_keyboard(lang),
        )

    elif query.data == "home":
        await query.edit_message_text(
            t(lang, "home_text"), parse_mode="HTML",
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
        if lang not in SUPPORTED_LANGS:
            lang = "uz"

        chat = query.message.chat if query.message else None
        user = query.from_user

        if chat and chat.type in ("group", "supergroup"):
            if not await is_admin(update, context):
                await query.answer(
                    t(get_language("chat", chat.id), "admin_only_lang"),
                    show_alert=True,
                )
                return
            set_language("chat", chat.id, lang)
        elif user:
            set_language("user", user.id, lang)
            register_user(user.id)

        await query.answer()

        if chat and chat.type == "private":
            await query.edit_message_text(
                tr(lang, "language_saved") + "\n\n" + t(lang, "home_text"),
                parse_mode="HTML",
                reply_markup=await main_keyboard(context, lang),
            )
        else:
            await query.edit_message_text(
                tr(lang, "language_saved"), parse_mode="HTML",
            )


# =========================================================
# PROTECT / UNPROTECT / STATUS / STATS
# =========================================================

async def _group_admin_guard(update, context):
    """(chat, message, lang) qaytaradi yoki None."""
    chat = update.effective_chat
    message = update.effective_message
    if not chat or not message:
        return None

    lang = language_for_update(update)

    if chat.type not in ("group", "supergroup"):
        await message.reply_text(tr(lang, "group_only"))
        return None

    return chat, message, lang


async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guard = await _group_admin_guard(update, context)
    if not guard:
        return
    chat, message, lang = guard

    if not await is_admin(update, context):
        await message.reply_text(t(lang, "admin_only"))
        return

    register_group(chat.id, chat.title or "Unknown")
    set_protection(chat.id, True)
    await message.reply_text(t(lang, "protect_long"), parse_mode="HTML")


async def unprotect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guard = await _group_admin_guard(update, context)
    if not guard:
        return
    chat, message, lang = guard

    if not await is_admin(update, context):
        await message.reply_text(t(lang, "admin_only"))
        return

    register_group(chat.id, chat.title or "Unknown")
    set_protection(chat.id, False)
    await message.reply_text(t(lang, "unprotect_long"), parse_mode="HTML")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guard = await _group_admin_guard(update, context)
    if not guard:
        return
    chat, message, lang = guard

    key = "status_on" if is_protection_enabled(chat.id) else "status_off"
    await message.reply_text(t(lang, key), parse_mode="HTML")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
    if not chat or not message:
        return

    lang = language_for_update(update)
    await message.reply_text(
        t(lang, "stats_title", total=get_stats(chat.id)),
        parse_mode="HTML",
    )


# =========================================================
# LINK IP / LOCATION LOOKUP
# =========================================================

def get_link_info(url: str):
    """
    Domen DNS orqali server IP manzilini aniqlaydi.
    Geo-ma'lumot server IP ga tegishli va taxminiy; linkni yuborgan odamning
    IP manzili yoki jismoniy manzili aniqlanmaydi.
    """
    try:
        clean_url = (url or "").strip().rstrip(".,!?;:)")
        if not clean_url:
            return None
        if not clean_url.lower().startswith(("http://", "https://")):
            clean_url = "https://" + clean_url

        parsed = urlparse(clean_url)
        domain = parsed.hostname
        if not domain:
            return None
        domain = domain.encode("idna").decode("ascii").lower()

        records = socket.getaddrinfo(domain, None, type=socket.SOCK_STREAM)
        ips = []
        for record in records:
            candidate = record[4][0]
            try:
                if ipaddress.ip_address(candidate).is_global and candidate not in ips:
                    ips.append(candidate)
            except ValueError:
                continue
        if not ips:
            return None

        ip = ips[0]
        country = city = isp = "?"
        try:
            request = urllib.request.Request(
                f"https://ipwho.is/{urllib.parse.quote(ip, safe='')}",
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

        return {"domain": domain, "ip": ip, "country": country, "city": city, "isp": isp}
    except Exception as e:
        logger.warning("Link IP aniqlash xatosi: %s", e)
        return None


async def build_link_block(url: str, lang: str, with_title: bool = False) -> str:
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
            t(lang, "geo_note"),
        ]
    else:
        lines.append(tr(lang, "ip_failed"))

    return "\n".join(lines)


# =========================================================
# MESSAGE SCANNER
# =========================================================

APK_EXTENSIONS = (".apk", ".xapk", ".apks", ".apkm")
APK_MIME_TYPES = (
    "application/vnd.android.package-archive",
    "application/x-authorware-bin",
)


def is_apk_document(document) -> bool:
    if not document:
        return False

    file_name = (document.file_name or "").lower().strip()
    mime_type = (document.mime_type or "").lower().strip()

    return file_name.endswith(APK_EXTENSIONS) or mime_type in APK_MIME_TYPES[:1]


def collect_text(message) -> str:
    """Matn + sarlavha + yashirin (text_link) havolalar."""
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or ()
    hidden = [e.url for e in entities if e.type == "text_link" and e.url]
    if hidden:
        text += "\n" + "\n".join(hidden)
    return text


async def scan_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat

    if not message or not chat:
        return

    if getattr(message, "business_connection_id", None):
        return

    is_private = chat.type == "private"
    is_group = chat.type in ("group", "supergroup")

    if not (is_private or is_group):
        return

    if is_group:
        known = context.bot_data.setdefault("known_groups", set())
        if chat.id not in known:
            register_group(chat.id, chat.title or "Unknown")
            known.add(chat.id)

        if not is_protection_enabled(chat.id):
            return

    user = update.effective_user
    if is_private and user:
        register_user(user.id)

    lang = language_for_update(update)
    username = user.mention_html() if user else "User"
    username_db = user.username if user and user.username else ""
    user_id = user.id if user else 0

    # 1) BARCHA APK FAYLLARNI O'CHIRISH
    if is_apk_document(message.document):
        deleted = True
        try:
            await message.delete()
        except Exception as e:
            deleted = False
            logger.warning("APK xabarini o'chirib bo'lmadi: %s", e)

        save_incident(
            chat.id, user_id, username_db,
            "APK:" + (message.document.file_name or "file")[:120],
        )

        try:
            scanning = await context.bot.send_message(
                chat_id=chat.id, text=tr(lang, "apk_title"), parse_mode="HTML",
            )
            await asyncio.sleep(0.7)
            await scanning.edit_text(
                tr(lang, "apk_blocked", user=username), parse_mode="HTML",
            )
            if not deleted and is_group:
                await context.bot.send_message(
                    chat_id=chat.id, text=t(lang, "cant_delete"),
                )
        except Exception as e:
            logger.warning("APK ogohlantirishida xato: %s", e)

        return

    # 2) LINKLARNI TAHLIL QILISH
    text = collect_text(message)
    if not text:
        return

    urls = extract_urls(text)
    if not urls:
        return

    dangerous_urls = scan_text(text)

    # ---------- Shaxsiy chat ----------
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
                chat_id=chat.id, text=result_text, parse_mode="HTML",
                disable_web_page_preview=True,
            )
        else:
            await message.reply_text(
                result_text, parse_mode="HTML", disable_web_page_preview=True,
            )
        return

    # ---------- Guruh ----------
    if not dangerous_urls:
        return

    blocks = [await build_link_block(url, lang) for url in dangerous_urls]

    for url in dangerous_urls:
        save_incident(chat.id, user_id, username_db, url)

    deleted = True
    try:
        await message.delete()
    except Exception as e:
        deleted = False
        logger.warning("Xabarni o'chirib bo'lmadi: %s", e)

    try:
        scanning = await context.bot.send_message(
            chat_id=chat.id, text=tr(lang, "scan_title"), parse_mode="HTML",
        )
        await asyncio.sleep(0.7)
        await scanning.edit_text(
            tr(lang, "phishing_blocked", user=username,
               details="\n\n".join(blocks)),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        if not deleted:
            await context.bot.send_message(
                chat_id=chat.id, text=t(lang, "cant_delete"),
            )
    except Exception as e:
        logger.error("Warning yuborishda xato: %s", e)


# =========================================================
# BUSINESS CHATLAR
# =========================================================

async def delete_business_message(context, connection_id: str, message_id: int):
    bot = context.bot

    if hasattr(bot, "delete_business_messages"):
        return await bot.delete_business_messages(
            business_connection_id=connection_id,
            message_ids=[message_id],
        )

    return await bot.do_api_request(
        "deleteBusinessMessages",
        api_kwargs={
            "business_connection_id": connection_id,
            "message_ids": [message_id],
        },
    )


async def get_business_conn(context, connection_id: str):
    conn = get_business_connection(connection_id)
    if conn:
        return conn

    try:
        bc = await context.bot.get_business_connection(connection_id)
        save_business_connection(bc)
        return get_business_connection(connection_id)
    except Exception as e:
        logger.warning("Business ulanishni olib bo'lmadi: %s", e)
        return None


async def business_connection_update(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    bc = update.business_connection
    if not bc:
        return

    save_business_connection(bc)
    lang = get_language("user", bc.user.id)

    if not bc.is_enabled:
        text = t(lang, "biz_disconnected")
    else:
        conn = get_business_connection(bc.id)
        text = t(lang, "biz_connected")
        if conn and not conn["can_delete"]:
            text += "\n\n" + t(lang, "biz_no_delete")

    try:
        await context.bot.send_message(
            chat_id=bc.user_chat_id, text=text, parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Business ulanish xabarini yuborib bo'lmadi: %s", e)


async def scan_business_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    message = update.business_message or update.edited_business_message

    if not message or not message.business_connection_id:
        return

    connection_id = message.business_connection_id
    conn = await get_business_conn(context, connection_id)

    if not conn or not conn["is_enabled"]:
        return

    owner_id = conn["user_id"]
    owner_chat_id = conn["user_chat_id"]
    sender = message.from_user

    if sender and sender.id == owner_id:
        return

    lang = get_language("user", owner_id)

    is_apk = is_apk_document(message.document)
    dangerous_urls = []

    if not is_apk:
        text = collect_text(message)
        if not text:
            return

        dangerous_urls = scan_text(text)
        if not dangerous_urls:
            return

    deleted = False
    try:
        await delete_business_message(context, connection_id, message.message_id)
        deleted = True
    except Exception as e:
        logger.warning("Business xabarni o'chirib bo'lmadi: %s", e)

    sender_id = sender.id if sender else 0
    sender_username = sender.username if sender and sender.username else ""

    for url in (dangerous_urls or ["APK"]):
        save_incident(owner_chat_id, sender_id, sender_username, url)

    sender_name = html.escape(sender.full_name) if sender else "?"
    if sender and sender.username:
        sender_name += f" (@{html.escape(sender.username)})"

    chat_name = html.escape(message.chat.full_name or str(message.chat.id))

    if is_apk:
        notice = t(lang, "biz_apk", sender=sender_name, chat=chat_name)
    else:
        blocks = [await build_link_block(u, lang) for u in dangerous_urls]
        notice = t(
            lang, "biz_phish", sender=sender_name, chat=chat_name,
            details="\n\n".join(blocks),
        )

    notice += "\n\n" + t(lang, "biz_deleted" if deleted else "biz_not_deleted")

    try:
        await context.bot.send_message(
            chat_id=owner_chat_id, text=notice, parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.warning("Egasiga ogohlantirish yuborilmadi: %s", e)


# =========================================================
# KIBERXAVFSIZLIK VIDEOSI (til bo'yicha)
# =========================================================

VIDEO_QUERIES = {
    "uz": [
        "kiberjinoyatchilikka qarshi kurash",
        "kiberjinoyat firibgarlik ogohlantirish",
        "Ichki ishlar vazirligi kiberjinoyat profilaktika",
        "plastik karta firibgarlik o'zbekcha",
        "Kiberxavfsizlik markazi firibgarlik",
    ],
    "ru": [
        "киберпреступность как защититься",
        "кибермошенники как не попасться",
        "мошенничество в интернете профилактика МВД",
        "борьба с киберпреступлениями",
    ],
    "en": [
        "how to protect yourself from cybercrime",
        "cybercrime prevention tips",
        "online fraud scams awareness",
        "fighting cybercrime explained",
    ],
}

CYBER_WORDS = {
    "uz": [
        "kiber", "jinoyat", "firibgar", "profilaktika", "xavfsizlik",
        "himoya", "qarshi", "karta", "phishing", "ogoh", "virus",
        "zararli", "akkaunt", "parol", "internet",
    ],
    "ru": [
        "киберпреступ", "преступ", "мошенн", "кибер", "фишинг", "взлом",
        "безопасн", "защит", "обман", "профилактик", "аккаунт", "пароль",
    ],
    "en": [
        "cybercrime", "cyber crime", "crime", "fraud", "scam", "phishing",
        "cyber", "hack", "malware", "identity theft", "prevention",
    ],
}

UZ_MARKERS = [
    "o'zbek", "o‘zbek", "uzbek", "jinoyat", "firibgar", "kiber",
    "xavfsizlik", "himoya", "profilaktika", "ogoh", "zararli",
]

TRUSTED_UZ_CHANNELS = [
    "kiberxavfsizlik markazi", "ichki ishlar vazirligi", "csecuz",
    "iiv", "profilaktika",
]

VIDEO_FALLBACK_TITLE = {
    "uz": "Kiberjinoyatlarga qarshi kurash bo‘yicha videolar",
    "ru": "Видео о борьбе с киберпреступностью",
    "en": "Videos on fighting cybercrime",
}

VIDEO_CACHE = {}
VIDEO_CACHE_TTL = 6 * 3600
_CYRILLIC = re.compile(r"[а-яёўқғҳ]")


def _walk_video_renderers(obj):
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if "videoRenderer" in cur:
                yield cur["videoRenderer"]
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)


def _video_matches(lang: str, title: str, owner: str) -> bool:
    tl, ol = title.lower(), owner.lower()
    has_cyr = bool(_CYRILLIC.search(tl))
    has_words = any(w in tl for w in CYBER_WORDS[lang])

    if lang == "ru":
        return has_cyr and has_words

    if lang == "en":
        ascii_ratio = sum(1 for c in title if ord(c) < 128) / max(1, len(title))
        return (not has_cyr) and ascii_ratio > 0.9 and has_words

    # uz
    trusted = any(h in ol for h in TRUSTED_UZ_CHANNELS)
    marker = any(m in tl for m in UZ_MARKERS)
    return (trusted or marker) and (has_words or trusted)


def fetch_videos_for_lang(lang: str, limit: int = 8):
    found, seen = [], set()
    hl = {"uz": "uz", "ru": "ru", "en": "en"}[lang]

    for query in VIDEO_QUERIES[lang]:
        try:
            params = urllib.parse.urlencode({
                "search_query": query,
                "sp": "EgIQAQ==",
                "hl": hl,
            })
            request = urllib.request.Request(
                "https://www.youtube.com/results?" + params,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36"
                    ),
                    "Accept-Language": f"{hl},en;q=0.8",
                    "Cookie": "CONSENT=YES+1; SOCS=CAI",
                },
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                page = response.read().decode("utf-8", errors="ignore")

            m = re.search(r"ytInitialData\s*=\s*", page)
            if not m:
                continue
            data, _ = json.JSONDecoder().raw_decode(page[m.end():])

            for vr in _walk_video_renderers(data):
                vid = vr.get("videoId")
                if not vid or vid in seen:
                    continue

                runs = (vr.get("title") or {}).get("runs") or []
                title = runs[0].get("text", "") if runs else ""
                oruns = (vr.get("ownerText") or {}).get("runs") or []
                owner = oruns[0].get("text", "") if oruns else ""
                length = (vr.get("lengthText") or {}).get("simpleText", "")

                # Jonli efir (davomiylik yo'q) va 1 soatdan uzun videolar o'tkazib yuboriladi.
                if not length or length.count(":") >= 2:
                    continue
                if not title or not _video_matches(lang, title, owner):
                    continue

                seen.add(vid)
                found.append({
                    "id": vid,
                    "title": title[:200],
                    "url": f"https://www.youtube.com/watch?v={vid}",
                })
                if len(found) >= limit:
                    return found

        except Exception as e:
            logger.warning("YouTube qidiruv xatosi (%s/%s): %s", lang, query, e)

    return found


async def get_videos(lang: str):
    lang = norm_lang(lang)
    cached = VIDEO_CACHE.get(lang)
    if cached and time.time() - cached[0] < VIDEO_CACHE_TTL:
        return cached[1]

    videos = await asyncio.to_thread(fetch_videos_for_lang, lang)
    if videos:
        VIDEO_CACHE[lang] = (time.time(), videos)
    elif cached:
        return cached[1]  # eski keshni ishlatamiz
    return videos


def get_last_video_id(lang: str):
    with db() as conn:
        row = conn.execute(
            "SELECT last_video_id FROM daily_video_by_lang WHERE lang = ?",
            (lang,),
        ).fetchone()
    return row[0] if row else None


def save_last_video_id(lang: str, video_id: str):
    with db() as conn:
        conn.execute("""
            INSERT INTO daily_video_by_lang (lang, last_video_id, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(lang) DO UPDATE SET
                last_video_id = excluded.last_video_id,
                updated_at = excluded.updated_at
        """, (lang, video_id, datetime.now().isoformat()))


async def pick_video(lang: str):
    """Tilga mos video tanlaydi. Topilmasa — YouTube qidiruv havolasi (fallback)."""
    lang = norm_lang(lang)
    videos = await get_videos(lang)

    if videos:
        last = get_last_video_id(lang)
        candidates = [v for v in videos if v["id"] != last] or videos
        return random.choice(candidates)

    query = VIDEO_QUERIES[lang][0]
    return {
        "id": None,
        "title": VIDEO_FALLBACK_TITLE[lang],
        "url": "https://www.youtube.com/results?"
               + urllib.parse.urlencode({"search_query": query}),
    }


def video_message_text(lang: str, video: dict, with_footer: bool = True) -> str:
    text = (
        f"{t(lang, 'video_title')}\n\n"
        f"🎥 <b>{html.escape(video['title'])}</b>\n\n"
        f"<a href=\"{html.escape(video['url'])}\">{t(lang, 'video_watch')}</a>"
    )
    if with_footer:
        text += "\n\n🛡️ <b>AntiPhish Guard</b>"
    return text


async def safe_send(bot, chat_id, text, **kwargs):
    """(ok, xato) qaytaradi. Flood-limitda bir marta qayta urinadi."""
    for attempt in range(2):
        try:
            await bot.send_message(chat_id=chat_id, text=text, **kwargs)
            return True, None
        except RetryAfter as e:
            await asyncio.sleep(float(e.retry_after) + 1)
        except Forbidden as e:
            return False, f"Forbidden: {e}"
        except BadRequest as e:
            return False, f"BadRequest: {e}"
        except TelegramError as e:
            return False, str(e)
    return False, "RetryAfter"


async def send_daily_cyber_video(context: ContextTypes.DEFAULT_TYPE):
    """Har kuni guruhlarga va botdan foydalangan shaxsiy chatlarga yuboradi."""
    with db() as conn:
        group_ids = [r[0] for r in conn.execute(
            "SELECT chat_id FROM groups WHERE enabled = 1 AND COALESCE(active, 1) = 1"
        ).fetchall()]
        user_ids = [r[0] for r in conn.execute(
            "SELECT user_id FROM users WHERE active = 1"
        ).fetchall()]

    targets = [("group", cid) for cid in group_ids]
    targets += [("user", uid) for uid in user_ids]

    if DAILY_VIDEO_CHAT_ID:
        try:
            extra_id = int(DAILY_VIDEO_CHAT_ID)
            if extra_id not in group_ids:
                targets.append(("group", extra_id))
        except ValueError:
            logger.warning("DAILY_VIDEO_CHAT_ID noto'g'ri: %s", DAILY_VIDEO_CHAT_ID)

    chosen = {}
    sent_langs = set()
    ok_count = 0

    for kind, chat_id in targets:
        lang = norm_lang(get_language("chat" if kind == "group" else "user", chat_id))

        if lang not in chosen:
            chosen[lang] = await pick_video(lang)
        video = chosen[lang]

        ok, err = await safe_send(
            context.bot, chat_id, video_message_text(lang, video),
            parse_mode="HTML", disable_web_page_preview=False,
        )

        if ok:
            ok_count += 1
            sent_langs.add(lang)
        else:
            logger.warning("Kunlik video %s ga yuborilmadi: %s", chat_id, err)
            if err and err.startswith("Forbidden"):
                if kind == "group":
                    mark_group_inactive(chat_id)
                else:
                    mark_user_inactive(chat_id)

        await asyncio.sleep(0.05)

    for lang in sent_langs:
        if chosen[lang]["id"]:
            save_last_video_id(lang, chosen[lang]["id"])

    logger.info("Kunlik video yuborildi: %d/%d", ok_count, len(targets))
    return ok_count, len(targets)


async def daily_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/video — tanlangan tilda kiberxavfsizlik videosini yuboradi."""
    message = update.effective_message
    if not update.effective_chat or not message:
        return

    lang = norm_lang(language_for_update(update))
    video = await pick_video(lang)

    await message.reply_text(
        video_message_text(lang, video, with_footer=False),
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
        time=dt_time(hour=DAILY_VIDEO_HOUR, minute=DAILY_VIDEO_MINUTE, tzinfo=tz),
        name="daily_cyber_video",
    )

    logger.info(
        "Kunlik video jobi: %02d:%02d (%s)",
        DAILY_VIDEO_HOUR, DAILY_VIDEO_MINUTE, DAILY_VIDEO_TZ,
    )


# =========================================================
# BOT GURUHGA QO'SHILDI / CHIQARILDI / ADMIN QILINDI
# =========================================================

async def bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member_update = update.my_chat_member
    if not member_update:
        return

    chat = update.effective_chat
    if not chat:
        return

    old_status = member_update.old_chat_member.status
    new_status = member_update.new_chat_member.status

    # Foydalanuvchi botni bloklagan / qayta ochgan.
    if chat.type == "private":
        if new_status == ChatMemberStatus.BANNED:
            mark_user_inactive(chat.id)
        elif new_status == ChatMemberStatus.MEMBER:
            register_user(chat.id)
        return

    if chat.type not in ("group", "supergroup"):
        return

    lang = get_language("chat", chat.id)

    if new_status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
        mark_group_inactive(chat.id)
        context.bot_data.setdefault("known_groups", set()).discard(chat.id)
        return

    if (
        new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR)
        and old_status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED)
    ):
        register_group(chat.id, chat.title or "Unknown")
        context.bot_data.setdefault("known_groups", set()).add(chat.id)

        try:
            await context.bot.send_message(
                chat_id=chat.id, text=t(lang, "welcome_group"), parse_mode="HTML",
            )
        except Exception as e:
            logger.error("Welcome message error: %s", e)

    if (
        new_status == ChatMemberStatus.ADMINISTRATOR
        and old_status != ChatMemberStatus.ADMINISTRATOR
    ):
        register_group(chat.id, chat.title or "Unknown")

        try:
            await context.bot.send_message(
                chat_id=chat.id, text=t(lang, "thanks_admin"), parse_mode="HTML",
            )
        except Exception as e:
            logger.error("Admin message error: %s", e)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Kutilmagan xato:", exc_info=context.error)


# =========================================================
# OWNER ADMIN PANEL
# =========================================================

PAGE_SIZE = 8


def admin_configured() -> bool:
    return bool(ADMIN_PASSWORD) and OWNER_TELEGRAM_ID != 0


def owner_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Umumiy statistika", callback_data="admin:stats")],
        [InlineKeyboardButton("👥 Guruhlar", callback_data="admin:groups:0")],
        [InlineKeyboardButton("📣 Hamma guruhga xabar", callback_data="admin:bc")],
        [InlineKeyboardButton("🎬 Videoni hozir yuborish", callback_data="admin:video")],
        [InlineKeyboardButton("🚨 Oxirgi hodisalar", callback_data="admin:incidents:0")],
        [InlineKeyboardButton("🔒 Chiqish", callback_data="admin:logout")],
    ])


def admin_home_button():
    return [InlineKeyboardButton("⬅️ Admin menyu", callback_data="admin:home")]


ADMIN_HOME_TEXT = "🛡️ <b>AntiPhish Guard — Admin panel</b>\n\nKerakli bo‘limni tanlang:"


def is_bot_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user or not admin_configured() or user.id != OWNER_TELEGRAM_ID:
        return False

    started = context.user_data.get("admin_authenticated_at")
    if not started:
        return False

    if time.time() - started > ADMIN_SESSION_SECONDS:
        context.user_data.pop("admin_authenticated_at", None)
        return False

    return True


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    if user and message:
        await message.reply_text(f"Telegram ID raqamingiz: {user.id}")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not user:
        return
    if not chat or chat.type != "private":
        await message.reply_text("❌ Admin panel faqat shaxsiy chatda ishlaydi.")
        return
    if not admin_configured():
        await message.reply_text(
            "⚠️ Admin panel sozlanmagan. .env faylida ADMIN_PASSWORD va "
            "OWNER_TELEGRAM_ID ni kiriting (ID ni /myid bilan bilib oling)."
        )
        return
    if user.id != OWNER_TELEGRAM_ID:
        await message.reply_text("❌ Sizda admin panelga kirish huquqi yo‘q.")
        return

    context.user_data.clear()
    context.user_data["admin_waiting_password"] = True
    await message.reply_text("🔐 Admin panel parolini kiriting:")


def _too_many_fails(context) -> bool:
    now = time.time()
    fails = [x for x in context.bot_data.get("admin_fails", []) if now - x < ADMIN_FAIL_WINDOW]
    context.bot_data["admin_fails"] = fails
    return len(fails) >= ADMIN_MAX_FAILS


async def send_to_chat(bot, chat_id: int, text: str):
    ok, err = await safe_send(bot, chat_id, text, disable_web_page_preview=True)
    if not ok and err and err.startswith("Forbidden"):
        mark_group_inactive(chat_id)
    return ok, err


async def admin_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parol kiritish va admin xabar yuborish holatlari (group=-1)."""
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not user or not chat or chat.type != "private":
        return

    ud = context.user_data

    # ---- Parol ----
    if ud.get("admin_waiting_password"):
        if not admin_configured() or user.id != OWNER_TELEGRAM_ID:
            ud.pop("admin_waiting_password", None)
            return

        supplied = (message.text or "").strip()
        try:
            await message.delete()
        except Exception:
            pass

        ud.pop("admin_waiting_password", None)

        if _too_many_fails(context):
            await context.bot.send_message(
                chat_id=chat.id,
                text="⛔ Juda ko‘p urinish. 15 daqiqadan keyin qayta urinib ko‘ring.",
            )
            raise ApplicationHandlerStop

        if not hmac.compare_digest(supplied.encode(), ADMIN_PASSWORD.encode()):
            context.bot_data.setdefault("admin_fails", []).append(time.time())
            await context.bot.send_message(
                chat_id=chat.id,
                text="❌ Parol noto‘g‘ri. Qayta kirish uchun /admin yuboring.",
            )
            raise ApplicationHandlerStop

        ud["admin_authenticated_at"] = time.time()
        await context.bot.send_message(
            chat_id=chat.id, text=ADMIN_HOME_TEXT, parse_mode="HTML",
            reply_markup=owner_admin_keyboard(),
        )
        raise ApplicationHandlerStop

    # ---- Xabar yuborish holatlari ----
    action = ud.get("admin_action")
    if not action:
        return

    if not is_bot_owner(update, context):
        ud.pop("admin_action", None)
        return

    text = message.text or ""
    ud.pop("admin_action", None)

    if action["type"] == "send":
        chat_id = action["chat_id"]
        ok, err = await send_to_chat(context.bot, chat_id, text)
        await message.reply_text(
            "✅ Xabar guruhga yuborildi." if ok else f"❌ Yuborilmadi: {err}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Guruh", callback_data=f"admin:g:{chat_id}:0")],
                admin_home_button(),
            ]),
        )
        raise ApplicationHandlerStop

    if action["type"] == "broadcast":
        ud["admin_pending_broadcast"] = text
        await message.reply_text(
            "📣 Quyidagi xabar HAMMA faol guruhlarga yuboriladi:\n\n"
            f"{text}\n\nTasdiqlaysizmi?",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Yuborish", callback_data="admin:bc_yes"),
                    InlineKeyboardButton("❌ Bekor qilish", callback_data="admin:cancel"),
                ]
            ]),
        )
        raise ApplicationHandlerStop


async def _edit(query, text, markup=None, html_mode=True):
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML" if html_mode else None,
            reply_markup=markup,
            disable_web_page_preview=True,
        )
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            logger.warning("Admin edit xatosi: %s", e)


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    if not is_bot_owner(update, context):
        await query.answer("❌ Ruxsat yo‘q. /admin orqali qayta kiring.", show_alert=True)
        return

    data = query.data or ""
    ud = context.user_data
    await query.answer()

    # ---- Chiqish / menyu / bekor ----
    if data == "admin:logout":
        ud.clear()
        await _edit(query, "🔒 Admin paneldan chiqdingiz. Qayta kirish: /admin", html_mode=False)
        return

    if data in ("admin:home", "admin:cancel"):
        ud.pop("admin_action", None)
        ud.pop("admin_pending_broadcast", None)
        await _edit(query, ADMIN_HOME_TEXT, owner_admin_keyboard())
        return

    # ---- Umumiy statistika ----
    if data == "admin:stats":
        with db() as conn:
            c = conn.cursor()
            groups_total = c.execute(
                "SELECT COUNT(*) FROM groups WHERE COALESCE(active,1)=1").fetchone()[0]
            groups_enabled = c.execute(
                "SELECT COUNT(*) FROM groups WHERE enabled=1 AND COALESCE(active,1)=1").fetchone()[0]
            incidents_total = c.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
            business_total = c.execute(
                "SELECT COUNT(*) FROM business_connections WHERE is_enabled=1").fetchone()[0]
            users_total = c.execute("SELECT COUNT(*) FROM users WHERE active=1").fetchone()[0]

        text = (
            "📊 <b>Umumiy statistika</b>\n\n"
            f"👥 Faol guruhlar: <b>{groups_total}</b>\n"
            f"🛡️ Himoyasi yoqilgan guruhlar: <b>{groups_enabled}</b>\n"
            f"👤 Botdan foydalangan shaxsiy chatlar: <b>{users_total}</b>\n"
            f"🚨 Jami hodisalar: <b>{incidents_total}</b>\n"
            f"💼 Faol Business ulanishlar: <b>{business_total}</b>"
        )
        await _edit(query, text, InlineKeyboardMarkup([admin_home_button()]))
        return

    # ---- Guruhlar ro'yxati ----
    if data.startswith("admin:groups:"):
        try:
            page = max(0, int(data.rsplit(":", 1)[1]))
        except ValueError:
            page = 0

        with db() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM groups WHERE COALESCE(active,1)=1").fetchone()[0]
            rows = conn.execute(
                "SELECT chat_id, title, enabled FROM groups WHERE COALESCE(active,1)=1 "
                "ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (PAGE_SIZE, page * PAGE_SIZE),
            ).fetchall()

        lines = [f"👥 <b>Guruhlar</b> — jami: {total}\n"]
        buttons = []
        for chat_id, title, enabled in rows:
            raw_title = title or "Noma’lum guruh"
            state = "🟢" if enabled else "🔴"
            lines.append(f"{state} <b>{html.escape(raw_title)}</b>\n<code>{chat_id}</code>")
            buttons.append([InlineKeyboardButton(
                f"{state} {raw_title[:40]}",
                callback_data=f"admin:g:{chat_id}:{page}",
            )])

        if not rows:
            lines.append("Hozircha guruhlar yo‘q.")

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"admin:groups:{page-1}"))
        if (page + 1) * PAGE_SIZE < total:
            nav.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"admin:groups:{page+1}"))
        if nav:
            buttons.append(nav)
        buttons.append(admin_home_button())

        await _edit(query, "\n\n".join(lines), InlineKeyboardMarkup(buttons))
        return

    # ---- Bitta guruh sahifasi ----
    if data.startswith("admin:g:"):
        try:
            _, _, raw_id, raw_page = data.split(":")
            chat_id, page = int(raw_id), int(raw_page)
        except (ValueError, TypeError):
            await _edit(query, "❌ Ma’lumot noto‘g‘ri.", InlineKeyboardMarkup([admin_home_button()]))
            return

        with db() as conn:
            row = conn.execute(
                "SELECT title, enabled FROM groups WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            incidents = conn.execute(
                "SELECT COUNT(*) FROM incidents WHERE chat_id = ?", (chat_id,)
            ).fetchone()[0]

        if not row:
            await _edit(query, "❌ Guruh topilmadi.", InlineKeyboardMarkup([admin_home_button()]))
            return

        title, enabled = row

        rights = "❓ noma’lum"
        try:
            me = await context.bot.get_chat_member(chat_id, context.bot.id)
            if me.status == ChatMemberStatus.ADMINISTRATOR:
                can_del = getattr(me, "can_delete_messages", False)
                rights = "✅ admin" + (", o‘chirish huquqi bor" if can_del else ", ❌ o‘chirish huquqi yo‘q")
            elif me.status == ChatMemberStatus.MEMBER:
                rights = "⚠️ oddiy a’zo (admin emas)"
            else:
                rights = "❌ guruhda yo‘q"
        except Exception:
            pass

        text = (
            f"👥 <b>{html.escape(title or 'Noma’lum guruh')}</b>\n\n"
            f"🆔 <code>{chat_id}</code>\n"
            f"🛡️ Himoya: {'🟢 yoqilgan' if enabled else '🔴 o‘chirilgan'}\n"
            f"🤖 Bot: {rights}\n"
            f"🚨 Hodisalar: <b>{incidents}</b>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✉️ Guruhga xabar yozish", callback_data=f"admin:send:{chat_id}")],
            [InlineKeyboardButton(
                "🔴 Himoyani o‘chirish" if enabled else "🟢 Himoyani yoqish",
                callback_data=f"admin:toggle:{chat_id}:{page}",
            )],
            [InlineKeyboardButton("⬅️ Guruhlar ro‘yxati", callback_data=f"admin:groups:{page}")],
            admin_home_button(),
        ])
        await _edit(query, text, kb)
        return

    # ---- Himoyani almashtirish ----
    if data.startswith("admin:toggle:"):
        try:
            _, _, raw_id, raw_page = data.split(":")
            chat_id, page = int(raw_id), int(raw_page)
        except (ValueError, TypeError):
            await _edit(query, "❌ Ma’lumot noto‘g‘ri.", InlineKeyboardMarkup([admin_home_button()]))
            return

        set_protection(chat_id, not is_protection_enabled(chat_id))
        query.data = f"admin:g:{chat_id}:{page}"
        await admin_panel_callback(update, context)
        return

    # ---- Bitta guruhga xabar ----
    if data.startswith("admin:send:"):
        try:
            chat_id = int(data.split(":", 2)[2])
        except (ValueError, IndexError):
            return
        ud["admin_action"] = {"type": "send", "chat_id": chat_id}
        await _edit(
            query,
            "✉️ Guruhga yuboriladigan xabar matnini yozing:",
            InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin:cancel")]]),
            html_mode=False,
        )
        return

    # ---- Hammaga xabar ----
    if data == "admin:bc":
        ud["admin_action"] = {"type": "broadcast"}
        await _edit(
            query,
            "📣 Hamma faol guruhlarga yuboriladigan xabar matnini yozing:",
            InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin:cancel")]]),
            html_mode=False,
        )
        return

    if data == "admin:bc_yes":
        text = ud.pop("admin_pending_broadcast", None)
        if not text:
            await _edit(query, "❌ Yuboriladigan xabar topilmadi.", InlineKeyboardMarkup([admin_home_button()]))
            return

        with db() as conn:
            chat_ids = [r[0] for r in conn.execute(
                "SELECT chat_id FROM groups WHERE COALESCE(active,1)=1").fetchall()]

        await _edit(query, f"⏳ Yuborilmoqda… ({len(chat_ids)} ta guruh)", html_mode=False)

        ok_count, failed = 0, []
        for cid in chat_ids:
            ok, err = await send_to_chat(context.bot, cid, text)
            if ok:
                ok_count += 1
            else:
                failed.append(cid)
            await asyncio.sleep(0.05)

        report = f"✅ Yuborildi: {ok_count}\n❌ Xato: {len(failed)}"
        if failed:
            report += "\n\nXato bo‘lgan ID lar:\n" + "\n".join(str(x) for x in failed[:20])
        await _edit(query, report, InlineKeyboardMarkup([admin_home_button()]), html_mode=False)
        return

    # ---- Videoni hozir yuborish ----
    if data == "admin:video":
        await _edit(query, "⏳ Video yuborilmoqda…", html_mode=False)
        ok_count, total = await send_daily_cyber_video(context)
        await _edit(
            query, f"🎬 Video yuborildi: {ok_count}/{total}",
            InlineKeyboardMarkup([admin_home_button()]), html_mode=False,
        )
        return

    # ---- Hodisalar ----
    if data.startswith("admin:incidents:"):
        try:
            page = max(0, int(data.rsplit(":", 1)[1]))
        except ValueError:
            page = 0

        with db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
            rows = conn.execute(
                "SELECT chat_id, username, url, created_at FROM incidents "
                "ORDER BY id DESC LIMIT ? OFFSET ?",
                (PAGE_SIZE, page * PAGE_SIZE),
            ).fetchall()

        lines = [f"🚨 <b>Oxirgi hodisalar</b> — jami: {total}\n"]
        for chat_id, username, url, created_at in rows:
            lines.append(
                f"• {html.escape(created_at or '')}\n"
                f"  Chat ID: <code>{chat_id}</code>\n"
                f"  Foydalanuvchi: {html.escape(username or '—')}\n"
                f"  Havola: <code>{html.escape((url or '')[:180])}</code>"
            )
        if not rows:
            lines.append("Hozircha hodisalar mavjud emas.")

        buttons, nav = [], []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"admin:incidents:{page-1}"))
        if (page + 1) * PAGE_SIZE < total:
            nav.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"admin:incidents:{page+1}"))
        if nav:
            buttons.append(nav)
        buttons.append(admin_home_button())

        await _edit(query, "\n\n".join(lines), InlineKeyboardMarkup(buttons))
        return

    await query.answer("Noma’lum amal.", show_alert=True)


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
    application.add_handler(CommandHandler("myid", myid_command))
    application.add_handler(CommandHandler("admin", admin_command))

    # Inline tugmalar
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
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern=r"^admin:"))

    # Bot guruhga qo'shilganda / chiqarilganda
    application.add_handler(
        ChatMemberHandler(bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER)
    )

    # Business
    application.add_handler(BusinessConnectionHandler(business_connection_update))
    application.add_handler(
        MessageHandler(filters.UpdateType.BUSINESS_MESSAGES, scan_business_message)
    )

    # Admin parol / xabar kiritish (scanner'dan oldin)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            admin_text_message,
        ),
        group=-1,
    )

    # Xabarlarni tekshirish (guruh + botga yozilgan shaxsiy chat)
    application.add_handler(
        MessageHandler(
            (filters.TEXT | filters.Document.ALL | filters.CaptionRegex(r".+"))
            & ~filters.COMMAND
            & ~filters.UpdateType.BUSINESS_MESSAGES,
            scan_message,
        )
    )

    application.add_error_handler(error_handler)

    setup_daily_video_job(application)

    print("\n===================================")
    print("🛡️ ANTIPHISH GUARD")
    print("===================================")
    print("Bot ishga tushdi...")
    print("===================================\n")

    if not admin_configured():
        logger.warning(
            "Admin panel o'chiq: ADMIN_PASSWORD va OWNER_TELEGRAM_ID o'rnatilmagan."
        )

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
