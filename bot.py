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

# Faqat loyiha egasi foydalana oladigan Admin Panel
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_connections (
            connection_id TEXT PRIMARY KEY,
            user_id INTEGER,
            user_chat_id INTEGER,
            is_enabled INTEGER DEFAULT 1,
            can_delete INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_business_connection(bc):
    """Telegram BusinessConnection obyektini bazaga saqlaydi."""
    rights = getattr(bc, "rights", None)
    can_delete = (
        bool(getattr(rights, "can_delete_all_messages", False))
        if rights is not None
        else True  # eski versiyalarda huquq ma'lum emas
    )

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
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
    conn.commit()
    conn.close()


def get_business_connection(connection_id: str):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, user_chat_id, is_enabled, can_delete
        FROM business_connections WHERE connection_id = ?
    """, (connection_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "user_id": row[0],
        "user_chat_id": row[1],
        "is_enabled": bool(row[2]),
        "can_delete": bool(row[3]),
    }


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

    chat = update.effective_chat

    # Shaxsiy chatda /start bosilganda AVVAL til tanlanadi.
    if chat and chat.type == "private":
        await message.reply_text(
            language_selection_text(),
            parse_mode="HTML",
            reply_markup=language_keyboard(),
        )
        return

    # Guruhda to'g'ridan-to'g'ri asosiy menyu (guruh tilida).
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

        # Shaxsiy chat: til tanlangach asosiy menyu chiqadi.
        if chat and chat.type == "private":
            await query.edit_message_text(
                tr(lang, "language_saved") + "\n\n" + t(lang, "home_text"),
                parse_mode="HTML",
                reply_markup=await main_keyboard(context, lang),
            )
        else:
            await query.edit_message_text(
                tr(lang, "language_saved"),
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

    # Business xabarlar alohida handlerda qayta ishlanadi.
    if getattr(message, "business_connection_id", None):
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
# BUSINESS CHATLAR (Telegram Premium: Settings -> Business -> Chatbots)
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

    # Baza tozalangan bo'lsa, Telegram'dan qayta so'raymiz.
    try:
        bc = await context.bot.get_business_connection(connection_id)
        save_business_connection(bc)
        return get_business_connection(connection_id)
    except Exception as e:
        logger.warning("Business ulanishni olib bo'lmadi: %s", e)
        return None


async def business_connection_update(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
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
            chat_id=bc.user_chat_id,
            text=text,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Business ulanish xabarini yuborib bo'lmadi: %s", e)


async def scan_business_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
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

    # Faqat boshqalardan kelgan xabarlar tekshiriladi.
    if sender and sender.id == owner_id:
        return

    lang = get_language("user", owner_id)

    is_apk = is_apk_document(message.document)
    dangerous_urls = []

    if not is_apk:
        text = message.text or message.caption or ""
        if not text:
            return

        dangerous_urls = scan_text(text)
        if not dangerous_urls:
            return  # Xavfsiz xabar: tegmaymiz.

    # Xabarni o'chirish.
    deleted = False
    try:
        await delete_business_message(context, connection_id, message.message_id)
        deleted = True
    except Exception as e:
        logger.warning("Business xabarni o'chirib bo'lmadi: %s", e)

    # Hodisani saqlash.
    sender_id = sender.id if sender else 0
    sender_username = sender.username if sender and sender.username else ""

    for url in (dangerous_urls or ["APK"]):
        save_incident(owner_chat_id, sender_id, sender_username, url)

    # Ogohlantirish faqat egasiga (bot bilan chatga) yuboriladi.
    sender_name = html.escape(sender.full_name) if sender else "?"
    if sender and sender.username:
        sender_name += f" (@{html.escape(sender.username)})"

    chat_name = html.escape(message.chat.full_name or str(message.chat.id))

    if is_apk:
        notice = t(lang, "biz_apk", sender=sender_name, chat=chat_name)
    else:
        blocks = [await build_link_block(u, lang) for u in dangerous_urls]
        notice = t(
            lang,
            "biz_phish",
            sender=sender_name,
            chat=chat_name,
            details="\n\n".join(blocks),
        )

    notice += "\n\n" + t(lang, "biz_deleted" if deleted else "biz_not_deleted")

    try:
        await context.bot.send_message(
            chat_id=owner_chat_id,
            text=notice,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.warning("Egasiga ogohlantirish yuborilmadi: %s", e)


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
# OWNER-ONLY ADMIN PANEL (mavjud funksiyalarga tegilmagan)
# =========================================================


def is_bot_owner(update: Update) -> bool:
    """Admin panel faqat .env dagi ADMIN_ID egasiga ochiladi."""
    user = update.effective_user
    return bool(user and ADMIN_ID > 0 and user.id == ADMIN_ID)


def owner_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Umumiy statistika", callback_data="admin:stats")],
        [InlineKeyboardButton("👥 Guruhlarni boshqarish", callback_data="admin:groups:0")],
        [InlineKeyboardButton("🚨 Oxirgi tahdidlar", callback_data="admin:incidents")],
        [InlineKeyboardButton("🔄 Yangilash", callback_data="admin:home")],
    ])


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_bot_owner(update):
        message = update.effective_message
        if message:
            await message.reply_text("⛔ Bu paneldan foydalanishga ruxsatingiz yo‘q.")
        return

    message = update.effective_message
    if message:
        await message.reply_text(
            "👑 <b>AntiPhish Guard — Admin Panel</b>\n\n"
            "Quyidagi bo‘limlardan birini tanlang.",
            parse_mode="HTML",
            reply_markup=owner_admin_keyboard(),
        )


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    if not is_bot_owner(update):
        await query.answer("⛔ Ruxsat yo‘q.", show_alert=True)
        return

    await query.answer()
    action = query.data or "admin:home"

    try:
        if action == "admin:home":
            await query.edit_message_text(
                "👑 <b>AntiPhish Guard — Admin Panel</b>\n\nBo‘limni tanlang:",
                parse_mode="HTML",
                reply_markup=owner_admin_keyboard(),
            )
            return

        if action == "admin:stats":
            conn = db_connect()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM groups")
            groups_total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM groups WHERE enabled = 1")
            groups_enabled = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM incidents")
            incidents_total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM business_connections WHERE is_enabled = 1")
            business_total = cur.fetchone()[0]
            conn.close()

            text = (
                "📊 <b>Bot statistikasi</b>\n\n"
                f"👥 Jami guruhlar: <b>{groups_total}</b>\n"
                f"🟢 Himoyasi yoqilgan guruhlar: <b>{groups_enabled}</b>\n"
                f"🚨 Bazadagi tahdid yozuvlari: <b>{incidents_total}</b>\n"
                f"💼 Faol Business ulanishlari: <b>{business_total}</b>"
            )
            await query.edit_message_text(
                text, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin:home")]])
            )
            return

        if action.startswith("admin:groups:"):
            try:
                offset = max(0, int(action.rsplit(":", 1)[1]))
            except (ValueError, IndexError):
                offset = 0

            conn = db_connect()
            cur = conn.cursor()
            cur.execute(
                "SELECT chat_id, title, enabled FROM groups ORDER BY created_at DESC LIMIT 8 OFFSET ?",
                (offset,),
            )
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) FROM groups")
            total = cur.fetchone()[0]
            conn.close()

            lines = ["👥 <b>Guruhlarni boshqarish</b>", ""]
            buttons = []
            if not rows:
                lines.append("Hozircha guruhlar topilmadi.")
            for chat_id, title, enabled in rows:
                safe_title = html.escape(title or str(chat_id))
                state = "🟢 Yoqilgan" if enabled else "🔴 O‘chirilgan"
                lines.append(f"{safe_title} (<code>{chat_id}</code>) — {state}")
                button_text = ("🔴 Himoyani o‘chirish" if enabled else "🟢 Himoyani yoqish")
                buttons.append([InlineKeyboardButton(button_text + f" · {safe_title[:22]}", callback_data=f"admin:toggle:{chat_id}:{0 if enabled else 1}:{offset}")])

            nav = []
            if offset > 0:
                nav.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"admin:groups:{max(0, offset-8)}"))
            if offset + 8 < total:
                nav.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"admin:groups:{offset+8}"))
            if nav:
                buttons.append(nav)
            buttons.append([InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin:home")])
            lines.append(f"\nJami: {total} ta guruh")
            await query.edit_message_text(
                "\n".join(lines), parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return

        if action.startswith("admin:toggle:"):
            parts = action.split(":")
            if len(parts) != 5:
                await query.edit_message_text("⚠️ Noto‘g‘ri so‘rov.", reply_markup=owner_admin_keyboard())
                return
            chat_id, enabled, offset = int(parts[2]), int(parts[3]), int(parts[4])
            conn = db_connect()
            cur = conn.cursor()
            cur.execute("UPDATE groups SET enabled = ? WHERE chat_id = ?", (enabled, chat_id))
            changed = cur.rowcount
            conn.commit()
            conn.close()
            if not changed:
                await query.edit_message_text(
                    "⚠️ Guruh bazadan topilmadi.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Guruhlar", callback_data=f"admin:groups:{offset}")]])
                )
                return
            # Mavjud set_protection va himoya logikasini o‘zgartirmaymiz;
            # bazadagi enabled qiymati yangilanadi.
            context.user_data["admin_notice"] = "🟢 Himoya yoqildi." if enabled else "🔴 Himoya o‘chirildi."
            # Qayta chizishda guruhlar ro‘yxatiga qaytadi.
            await query.edit_message_text(
                ("🟢 Himoya yoqildi.\n\n" if enabled else "🔴 Himoya o‘chirildi.\n\n") + "Guruhlar ro‘yxati:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Guruhlarga qaytish", callback_data=f"admin:groups:{offset}")], [InlineKeyboardButton("🏠 Admin Panel", callback_data="admin:home")]])
            )
            return

        if action == "admin:incidents":
            conn = db_connect()
            cur = conn.cursor()
            cur.execute("SELECT chat_id, username, url, created_at FROM incidents ORDER BY id DESC LIMIT 10")
            rows = cur.fetchall()
            conn.close()

            lines = ["🚨 <b>Oxirgi tahdidlar</b>", ""]
            if not rows:
                lines.append("Hozircha tahdid yozuvlari yo‘q.")
            for chat_id, username, url, created_at in rows:
                safe_user = html.escape(username or "Noma’lum")
                safe_url = html.escape(url or "")
                safe_date = html.escape(created_at or "")
                lines.append(f"• <b>{safe_user}</b> | chat <code>{chat_id}</code>\n{safe_url}\n<i>{safe_date}</i>\n")
            await query.edit_message_text(
                "\n".join(lines), parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin:home")]])
            )
            return

        await query.edit_message_text(
            "👑 <b>Admin Panel</b>", parse_mode="HTML",
            reply_markup=owner_admin_keyboard(),
        )
    except Exception:
        logger.exception("Admin panel xatosi")
        try:
            await query.edit_message_text(
                "⚠️ Admin panelda xatolik yuz berdi. Loglarni tekshiring.",
                reply_markup=owner_admin_keyboard(),
            )
        except Exception:
            pass


# =========================================================
# MAIN
# =========================================================

def main():
    init_db()
    init_language_db()

    application = Application.builder().token(BOT_TOKEN).build()

    # Faqat loyiha egasi uchun Admin Panel
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern=r"^admin:"))

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

    # Business ulanish (Premium: Settings -> Business -> Chatbots)
    application.add_handler(
        BusinessConnectionHandler(business_connection_update)
    )

    # Business chatlardagi xabarlar (OLDIN turishi shart)
    application.add_handler(
        MessageHandler(
            filters.UpdateType.BUSINESS_MESSAGES,
            scan_business_message,
        )
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
