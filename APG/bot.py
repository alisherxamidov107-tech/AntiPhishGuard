import os
import sqlite3
import logging
from datetime import datetime

from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ChatMemberHandler,
    filters,
)

from services.scanner import scan_text


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

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

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
        logger.error("Admin tekshirish xatosi: %s", e)
        return False


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🛡️ <b>AntiPhish Guard</b>\n\n"
        "Telegram guruhlaringizni phishing va "
        "shubhali havolalardan himoya qiladi.\n\n"
        "📌 Botni guruhga qo‘shing va admin huquqi bering.\n\n"
        "Buyruqlar:\n"
        "/protect — himoyani yoqish\n"
        "/unprotect — himoyani o‘chirish\n"
        "/stats — statistika\n"
        "/status — holat"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )


# =========================================================
# GROUP SETUP
# =========================================================

async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):

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

    set_protection(chat.id, True)

    await update.message.reply_text(
        "🛡️ <b>APG himoyasi yoqildi!</b>\n\n"
        "Endi guruhdagi havolalar tekshiriladi.",
        parse_mode="HTML"
    )


async def unprotect(update: Update, context: ContextTypes.DEFAULT_TYPE):

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
        "🔓 APG himoyasi vaqtincha o‘chirildi."
    )


# =========================================================
# STATUS
# =========================================================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.effective_chat:
        return

    enabled = is_protection_enabled(
        update.effective_chat.id
    )

    if enabled:
        text = "🟢 APG himoyasi faol."
    else:
        text = "🔴 APG himoyasi o‘chiq."

    await update.message.reply_text(text)


# =========================================================
# STATS
# =========================================================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.effective_chat:
        return

    total = get_stats(
        update.effective_chat.id
    )

    await update.message.reply_text(
        f"📊 <b>APG statistikasi</b>\n\n"
        f"🛡️ Aniqlangan hodisalar: <b>{total}</b>",
        parse_mode="HTML"
    )


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

    # Faqat guruhlar
    if chat.type not in ["group", "supergroup"]:
        return

    # Himoya o'chirilgan bo'lsa
    if not is_protection_enabled(chat.id):
        return

    text = message.text or message.caption or ""

    if not text:
        return

    dangerous_urls = scan_text(text)

    if not dangerous_urls:
        return

    # Hodisalarni saqlash
    user = update.effective_user

    for url in dangerous_urls:

        save_incident(
            chat_id=chat.id,
            user_id=user.id if user else 0,
            username=user.username if user else "",
            url=url,
        )

    # Xabarni o'chirish
    try:
        await message.delete()

    except Exception as e:
        logger.warning(
            "Xabarni o'chirib bo'lmadi: %s",
            e
        )

    # Ogohlantirish
    username = user.mention_html() if user else "Foydalanuvchi"

    warning = (
        "🚨 <b>PHISHING ANIQLANDI!</b>\n\n"
        f"👤 {username}\n"
        "🔗 Shubhali havola aniqlanib, "
        "xabar o‘chirildi.\n\n"
        "🛡️ <b>AntiPhish Guard</b>"
    )

    try:
        warning_message = await context.bot.send_message(
            chat_id=chat.id,
            text=warning,
            parse_mode="HTML",
        )

        # 15 soniyadan keyin warningni o'chirish
        context.job_queue.run_once(
            delete_warning,
            15,
            data={
                "chat_id": chat.id,
                "message_id": warning_message.message_id,
            }
        )

    except Exception as e:
        logger.error(
            "Ogohlantirish yuborishda xato: %s",
            e
        )


async def delete_warning(context: ContextTypes.DEFAULT_TYPE):

    data = context.job.data

    try:
        await context.bot.delete_message(
            chat_id=data["chat_id"],
            message_id=data["message_id"],
        )

    except Exception:
        pass


# =========================================================
# BOT GROUP STATUS
# =========================================================

async def bot_added_to_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    member_update = update.my_chat_member

    if not member_update:
        return

    new_status = member_update.new_chat_member.status

    if new_status in [
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
    ]:

        chat = update.effective_chat

        register_group(
            chat.id,
            chat.title or "Unknown"
        )

        try:
            await context.bot.send_message(
                chat.id,
                "🛡️ <b>AntiPhish Guard</b> ishga tushdi!\n\n"
                "Phishing va shubhali havolalarni "
                "aniqlash uchun tayyorman.\n\n"
                "⚠️ Eng yaxshi himoya uchun menga "
                "admin huquqi bering.",
                parse_mode="HTML"
            )

        except Exception as e:
            logger.error(
                "Welcome message error: %s",
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

    # Commands
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("protect", protect)
    )

    application.add_handler(
        CommandHandler("unprotect", unprotect)
    )

    application.add_handler(
        CommandHandler("status", status)
    )

    application.add_handler(
        CommandHandler("stats", stats)
    )

    # Group join/status
    application.add_handler(
        ChatMemberHandler(
            bot_added_to_group,
            ChatMemberHandler.MY_CHAT_MEMBER
        )
    )

    # Messages
    application.add_handler(
        MessageHandler(
            filters.TEXT | filters.CaptionRegex(r".+"),
            scan_message
        )
    )

    print("===================================")
    print("🛡️ AntiPhish Guard ishga tushdi")
    print("===================================")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()