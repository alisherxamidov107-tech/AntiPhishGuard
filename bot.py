import os
import re
import html
import json
import socket
import sqlite3
import logging
import asyncio
import ipaddress
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
    BotCommand,
)
from telegram.constants import ChatMemberStatus, ParseMode
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
from telegram.error import TelegramError

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
# QO'SHIMCHA MATNLAR
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
    text = table.get(key)

    if text is None:
        # i18n dan olishga harakat qilamiz
        try:
            text = tr(lang, key, **kwargs)
            return text
        except Exception:
            text = EXTRA["uz"].get(key, key)

    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


# =========================================================
# DATABASE
# =========================================================

DB_NAME = os.getenv("DB_NAME", "database.db")


def db_connect():
    conn = sqlite3.connect(DB_NAME, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


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
    rights = getattr(bc, "rights", None)
    can_delete = (
        bool(getattr(rights, "can_delete_all_messages", False))
        if rights is not None
        else True
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
    if update.effective_chat.type not in ("group", "supergroup"):
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
    except TelegramError as e:
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
    if not query:
        return
    await query.answer()

    lang = language_for_update(update)

    try:
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
    except TelegramError as e:
        logger.warning("Menu callback xatosi: %s", e)


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
    if not query:
        return
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

    if chat.type not in ("group", "
