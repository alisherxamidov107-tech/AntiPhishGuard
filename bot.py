import os
import sqlite3
import logging
from datetime import datetime

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
            "ogohlantirish yuboriladi."
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

    if chat.type not in [
        "group",
        "supergroup"
    ]:
        return

    if not is_protection_enabled(chat.id):
        return
    # APK fayllarni avtomatik o‘chirish
    if message.document:
        file_name = (message.document.file_name or "").lower()
        mime_type = (message.document.mime_type or "").lower()

        if (
            file_name.endswith(".apk")
            or mime_type == "application/vnd.android.package-archive"
        ):
            try:
                await message.delete()

                warning = await context.bot.send_message(
                    chat_id=chat.id,
                    text=(
                        "🚫 <b>APK fayl o‘chirildi!</b>\n\n"
                        "🛡️ Ushbu guruhda APK fayllarni yuborish taqiqlangan.\n"
                        "🛡️ <b>AntiPhish Guard</b>"
                    ),
                    parse_mode="HTML"
                )

                context.job_queue.run_once(
                    delete_warning,
                    10,
                    data={
                        "chat_id": chat.id,
                        "message_id": warning.message_id,
                    }
                )

            except Exception as e:
                logger.warning(
                    "APK faylni o‘chirishda xato: %s",
                    e
                )

            return


    text = (
        message.text
        or message.caption
        or ""
    )

    if not text:
        return

    dangerous_urls = scan_text(text)

    if not dangerous_urls:
        return

    user = update.effective_user

    for url in dangerous_urls:

        save_incident(
            chat_id=chat.id,
            user_id=user.id if user else 0,
            username=user.username if user else "",
            url=url,
        )

    try:

        await message.delete()

    except Exception as e:

        logger.warning(
            "Xabarni o‘chirib bo‘lmadi: %s",
            e
        )

    username = (
        user.mention_html()
        if user
        else "Foydalanuvchi"
    )

    warning = (
        "🚨 <b>PHISHING ANIQLANDI!</b>\n\n"
        f"👤 {username}\n"
        "🔗 Shubhali havola aniqlandi.\n"
        "🗑️ Xabar o‘chirildi.\n\n"
        "🛡️ <b>AntiPhish Guard</b>"
    )

    try:

        warning_message = (
            await context.bot.send_message(
                chat_id=chat.id,
                text=warning,
                parse_mode="HTML",
            )
        )

        context.job_queue.run_once(
            delete_warning,
            15,
            data={
                "chat_id": chat.id,
                "message_id":
                    warning_message.message_id,
            }
        )

    except Exception as e:

        logger.error(
            "Warning yuborishda xato: %s",
            e
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

    # Bot guruhga qo‘shilgan holat
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

                "✅ Bot guruhga muvaffaqiyatli qo‘shildi!\n\n"

                "🔐 Men guruhdagi havolalarni "
                "tekshiraman va shubhali phishing "
                "linklarini aniqlashga harakat qilaman.\n\n"

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

    # Bot admin qilingan holat
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
                    "🔐 Himoya ishlashga tayyor."
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

    # Inline buttons
    application.add_handler(
        CallbackQueryHandler(menu_callback)
    )
    # Bot groupga qo‘shilganda
    application.add_handler(
        ChatMemberHandler(
            bot_added_to_group,
            ChatMemberHandler.MY_CHAT_MEMBER
        )
    )

    # Group messages
    application.add_handler(
        MessageHandler(
            filters.TEXT | filters.Document.ALL | filters.CaptionRegex(r".+"),
            scan_message
        )
    )

    print("")
    print("===================================")
    print("🛡️ ANTIPHISH GUARD")
    print("===================================")
    print("Bot ishga tushdi...")
    print("===================================")
    print("")

    # Render Free Web Service uchun webhook.
    # Lokal kompyuterda esa odatdagi polling ishlaydi.
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
        application.run_polling(
            allowed_updates=Update.ALL_TYPES
        )


if __name__ == "__main__":
    main()