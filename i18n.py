"""
AntiPhish Guard — multilingual support (UZ/RU/EN)
Compatible with python-telegram-bot v20+.

This module adds language preference storage and translated UI strings.
It does not replace the existing scanner/database logic.
"""
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

DB_NAME = "database.db"
SUPPORTED_LANGUAGES = {"uz", "ru", "en"}

TEXTS = {
    "uz": {
        "choose_language": "🌍 <b>Tilni tanlang</b>\n\nAntiPhish Guard qaysi tilda ishlasin?",
        "language_saved": "✅ Til o‘zgartirildi: <b>O‘zbek tili</b>",
        "language_menu": "🌍 Til / Language / Язык",
        "start_title": "🛡️ <b>AntiPhish Guard</b>",
        "start_description": "🔐 Telegram guruhlaringizni phishing va shubhali havolalardan himoya qiluvchi xavfsizlik boti.",
        "features_title": "⚡ <b>Asosiy imkoniyatlar:</b>",
        "feature_links": "• 🔗 Havolalarni tekshirish",
        "feature_phishing": "• 🚨 Phishingni aniqlash",
        "feature_delete": "• 🗑️ Xavfli xabarlarni o‘chirish",
        "feature_apk": "• 📦 APK fayllarni bloklash",
        "feature_stats": "• 📊 Hodisalar statistikasi",
        "feature_manage": "• ⚙️ Guruh himoyasini boshqarish",
        "start_choose": "👇 Kerakli bo‘limni tanlang:",
        "add_group": "➕ Guruhga qo‘shish",
        "guide": "📖 Qo‘llanma",
        "protection": "🛡️ Himoya",
        "statistics": "📊 Statistika",
        "back": "⬅️ Orqaga",
        "admin_only": "❌ Bu buyruq faqat administratorlar uchun.",
        "protection_on": "🛡️ <b>APG himoyasi yoqildi!</b>\n\n🔗 Havolalar tekshiriladi.\n🚨 Shubhali linklar aniqlanadi.\n📦 APK fayllar bloklanadi.\n🗑️ Xavfli xabarlar o‘chiriladi.",
        "protection_off": "🔴 <b>APG himoyasi o‘chirildi.</b>",
        "status_on": "🟢 <b>APG faol</b>\n\n🛡️ Guruh himoyalangan.",
        "status_off": "🔴 <b>APG o‘chiq</b>\n\nHimoya vaqtincha o‘chirilgan.",
        "stats_title": "📊 <b>APG statistikasi</b>\n\n🚨 Aniqlangan hodisalar: <b>{total}</b>",
        "stats_private": "📊 Statistikani ko‘rish uchun APG guruh ichida ishlashi kerak.",
        "link_analysis": "🔎 <b>LINK TAHLILI</b>",
        "domain": "🌐 Domen",
        "server_ip": "📡 Server IP",
        "country": "🌍 Davlat",
        "city": "🏙 Taxminiy shahar",
        "isp": "🏢 ISP/Hosting",
        "approx_location": "ℹ️ <i>Joylashuv IP bo‘yicha taxminiy.</i>",
        "ip_failed": "❌ Server IP ma’lumotini aniqlab bo‘lmadi.",
        "danger_title": "🚨 <b>DIQQAT! XAVF ANIQLANDI!</b>",
        "danger_link": "🔗 <b>XAVFLI LINK ANIQLANDI!</b>",
        "user": "👤 Foydalanuvchi",
        "blocked": "🔴 Status: <b>BLOKLANDI</b>",
        "risk_phishing": "⚠️ Risk: <b>PHISHING</b>",
        "dont_open": "🚫 <b>BU HAVOLAGA KIRMANG!</b>",
        "message_deleted": "Xabar xavfsizlik sababli o‘chirildi.",
        "brand": "🛡️ <b>AntiPhish Guard</b>",
        "scan_title": "🔎 <b>SECURITY SCAN</b>\n\n🔗 Havola tekshirilmoqda...\n⏳ Iltimos kuting...",
        "scan_analysis": "🛡️ <b>ANTI-PHISH GUARD</b>\n\n🔍 Havola tahlil qilinmoqda...\n🌐 Server ma’lumotlari aniqlanmoqda...",
        "scan_detected": "🚨 <b>THREAT DETECTED</b>\n\n❌ Xavfli havola aniqlandi!\n🛑 Xabar bloklanmoqda...",
        "apk_scan": "🔎 <b>SECURITY SCAN</b>\n\n📦 APK fayl tekshirilmoqda...\n⏳ Iltimos kuting...",
        "apk_analysis": "🛡️ <b>ANTI-PHISH GUARD</b>\n\n🔍 APK fayl tahlil qilinmoqda...\n⚠️ Xavfsizlik tekshiruvi davom etmoqda...",
        "apk_detected": "🚨 <b>THREAT DETECTED</b>\n\n❌ Xavfli APK aniqlandi!\n🛑 Fayl bloklanmoqda...",
        "apk_blocked": "🚨 <b>DIQQAT! XAVF ANIQLANDI!</b>\n\n📦 <b>APK FAYL BLOKLANDI!</b>\n\n👤 Foydalanuvchi: {user}\n🔴 Status: <b>BLOKLANDI</b>\n📱 Turi: ANDROID APK\n\n⚠️ Ushbu fayl xavfsizlik sababli guruhdan o‘chirildi.\n\n🛡️ <b>AntiPhish Guard</b>",
        "daily_video_title": "🇺🇿 <b>KUNNING KIBERXAVFSIZLIK VIDEOSI</b>",
        "daily_video_description": "🛡️ O‘zbekcha kiberxavfsizlik mavzusidagi foydali va himoyalanishga oid video.",
        "watch_video": "▶️ Videoni ko‘rish",
        "no_video": "❌ Hozircha ishonchli o‘zbekcha kiberxavfsizlik videosi topilmadi.",
        "guide_text": "📖 <b>APG qo‘llanmasi</b>\n\n1️⃣ APG’ni guruhga qo‘shing.\n2️⃣ Botni administrator qiling.\n3️⃣ Xabarlarni o‘chirish huquqini bering.\n4️⃣ Group Privacy sozlamasini o‘chiring.\n\nShundan keyin APG guruhdagi xabarlarni tekshira oladi.",
        "protection_text": "🛡️ <b>APG himoyasi</b>\n\n🔗 URL scanning — ON\n🚨 Phishing detection — ON\n📦 APK protection — ON\n🗑️ Xavfli xabarlarni o‘chirish — ON\n📊 Incident logging — ON\n\nHimoya guruh bo‘yicha alohida boshqariladi.",
    },
    "ru": {
        "choose_language": "🌍 <b>Выберите язык</b>\n\nНа каком языке должен работать AntiPhish Guard?",
        "language_saved": "✅ Язык изменён: <b>Русский</b>",
        "language_menu": "🌍 Язык / Language / Til",
        "start_title": "🛡️ <b>AntiPhish Guard</b>",
        "start_description": "🔐 Бот защищает ваши группы Telegram от фишинга и подозрительных ссылок.",
        "features_title": "⚡ <b>Основные возможности:</b>",
        "feature_links": "• 🔗 Проверка ссылок",
        "feature_phishing": "• 🚨 Обнаружение фишинга",
        "feature_delete": "• 🗑️ Удаление опасных сообщений",
        "feature_apk": "• 📦 Блокировка APK-файлов",
        "feature_stats": "• 📊 Статистика инцидентов",
        "feature_manage": "• ⚙️ Управление защитой группы",
        "start_choose": "👇 Выберите нужный раздел:",
        "add_group": "➕ Добавить в группу",
        "guide": "📖 Инструкция",
        "protection": "🛡️ Защита",
        "statistics": "📊 Статистика",
        "back": "⬅️ Назад",
        "admin_only": "❌ Эта команда доступна только администраторам.",
        "protection_on": "🛡️ <b>Защита APG включена!</b>\n\n🔗 Ссылки проверяются.\n🚨 Подозрительные ссылки выявляются.\n📦 APK-файлы блокируются.\n🗑️ Опасные сообщения удаляются.",
        "protection_off": "🔴 <b>Защита APG отключена.</b>",
        "status_on": "🟢 <b>APG активен</b>\n\n🛡️ Группа защищена.",
        "status_off": "🔴 <b>APG выключен</b>\n\nЗащита временно отключена.",
        "stats_title": "📊 <b>Статистика APG</b>\n\n🚨 Обнаружено инцидентов: <b>{total}</b>",
        "stats_private": "📊 Для просмотра статистики бот должен работать в группе.",
        "link_analysis": "🔎 <b>АНАЛИЗ ССЫЛКИ</b>",
        "domain": "🌐 Домен",
        "server_ip": "📡 IP сервера",
        "country": "🌍 Страна",
        "city": "🏙 Примерный город",
        "isp": "🏢 ISP/Хостинг",
        "approx_location": "ℹ️ <i>Местоположение приблизительное и определено по IP сервера.</i>",
        "ip_failed": "❌ Не удалось определить данные IP сервера.",
        "danger_title": "🚨 <b>ВНИМАНИЕ! ОБНАРУЖЕНА УГРОЗА!</b>",
        "danger_link": "🔗 <b>ОБНАРУЖЕНА ОПАСНАЯ ССЫЛКА!</b>",
        "user": "👤 Пользователь",
        "blocked": "🔴 Статус: <b>ЗАБЛОКИРОВАНО</b>",
        "risk_phishing": "⚠️ Риск: <b>ФИШИНГ</b>",
        "dont_open": "🚫 <b>НЕ ПЕРЕХОДИТЕ ПО ЭТОЙ ССЫЛКЕ!</b>",
        "message_deleted": "Сообщение удалено в целях безопасности.",
        "brand": "🛡️ <b>AntiPhish Guard</b>",
        "scan_title": "🔎 <b>ПРОВЕРКА БЕЗОПАСНОСТИ</b>\n\n🔗 Проверяем ссылку...\n⏳ Пожалуйста, подождите...",
        "scan_analysis": "🛡️ <b>ANTI-PHISH GUARD</b>\n\n🔍 Анализируем ссылку...\n🌐 Определяем данные сервера...",
        "scan_detected": "🚨 <b>ОБНАРУЖЕНА УГРОЗА</b>\n\n❌ Обнаружена опасная ссылка!\n🛑 Сообщение блокируется...",
        "apk_scan": "🔎 <b>ПРОВЕРКА БЕЗОПАСНОСТИ</b>\n\n📦 Проверяем APK-файл...\n⏳ Пожалуйста, подождите...",
        "apk_analysis": "🛡️ <b>ANTI-PHISH GUARD</b>\n\n🔍 Анализ APK-файла...\n⚠️ Проверка безопасности продолжается...",
        "apk_detected": "🚨 <b>ОБНАРУЖЕНА УГРОЗА</b>\n\n❌ Обнаружен потенциально опасный APK!\n🛑 Файл блокируется...",
        "apk_blocked": "🚨 <b>ВНИМАНИЕ! ОБНАРУЖЕНА УГРОЗА!</b>\n\n📦 <b>APK-ФАЙЛ ЗАБЛОКИРОВАН!</b>\n\n👤 Пользователь: {user}\n🔴 Статус: <b>ЗАБЛОКИРОВАНО</b>\n📱 Тип: ANDROID APK\n\n⚠️ Файл удалён из группы в целях безопасности.\n\n🛡️ <b>AntiPhish Guard</b>",
        "daily_video_title": "🇺🇿 <b>ВИДЕО ДНЯ ПО КИБЕРБЕЗОПАСНОСТИ</b>",
        "daily_video_description": "🛡️ Полезное видео на узбекском языке о кибербезопасности и защите.",
        "watch_video": "▶️ Смотреть видео",
        "no_video": "❌ Пока не удалось найти проверенное узбекское видео о кибербезопасности.",
        "guide_text": "📖 <b>Инструкция APG</b>\n\n1️⃣ Добавьте APG в группу.\n2️⃣ Назначьте бота администратором.\n3️⃣ Разрешите удалять сообщения.\n4️⃣ Отключите Group Privacy.\n\nПосле этого APG сможет проверять сообщения в группе.",
        "protection_text": "🛡️ <b>Защита APG</b>\n\n🔗 Проверка URL — ВКЛ\n🚨 Обнаружение фишинга — ВКЛ\n📦 Защита от APK — ВКЛ\n🗑️ Удаление опасных сообщений — ВКЛ\n📊 Журнал инцидентов — ВКЛ\n\nЗащита настраивается отдельно для каждой группы.",
    },
    "en": {
        "choose_language": "🌍 <b>Choose a language</b>\n\nWhich language should AntiPhish Guard use?",
        "language_saved": "✅ Language changed: <b>English</b>",
        "language_menu": "🌍 Language / Язык / Til",
        "start_title": "🛡️ <b>AntiPhish Guard</b>",
        "start_description": "🔐 A security bot that protects your Telegram groups from phishing and suspicious links.",
        "features_title": "⚡ <b>Main features:</b>",
        "feature_links": "• 🔗 Link scanning",
        "feature_phishing": "• 🚨 Phishing detection",
        "feature_delete": "• 🗑️ Deleting dangerous messages",
        "feature_apk": "• 📦 APK file blocking",
        "feature_stats": "• 📊 Incident statistics",
        "feature_manage": "• ⚙️ Group protection controls",
        "start_choose": "👇 Choose an option:",
        "add_group": "➕ Add to group",
        "guide": "📖 Guide",
        "protection": "🛡️ Protection",
        "statistics": "📊 Statistics",
        "back": "⬅️ Back",
        "admin_only": "❌ This command is available to group administrators only.",
        "protection_on": "🛡️ <b>APG protection enabled!</b>\n\n🔗 Links will be checked.\n🚨 Suspicious links will be detected.\n📦 APK files will be blocked.\n🗑️ Dangerous messages will be deleted.",
        "protection_off": "🔴 <b>APG protection disabled.</b>",
        "status_on": "🟢 <b>APG is active</b>\n\n🛡️ The group is protected.",
        "status_off": "🔴 <b>APG is disabled</b>\n\nProtection is temporarily turned off.",
        "stats_title": "📊 <b>APG statistics</b>\n\n🚨 Incidents detected: <b>{total}</b>",
        "stats_private": "📊 The bot must be active in a group to show group statistics.",
        "link_analysis": "🔎 <b>LINK ANALYSIS</b>",
        "domain": "🌐 Domain",
        "server_ip": "📡 Server IP",
        "country": "🌍 Country",
        "city": "🏙 Approximate city",
        "isp": "🏢 ISP/Hosting",
        "approx_location": "ℹ️ <i>Location is approximate and based on the server IP.</i>",
        "ip_failed": "❌ Could not determine the server IP information.",
        "danger_title": "🚨 <b>WARNING! THREAT DETECTED!</b>",
        "danger_link": "🔗 <b>DANGEROUS LINK DETECTED!</b>",
        "user": "👤 User",
        "blocked": "🔴 Status: <b>BLOCKED</b>",
        "risk_phishing": "⚠️ Risk: <b>PHISHING</b>",
        "dont_open": "🚫 <b>DO NOT OPEN THIS LINK!</b>",
        "message_deleted": "The message was deleted for security reasons.",
        "brand": "🛡️ <b>AntiPhish Guard</b>",
        "scan_title": "🔎 <b>SECURITY SCAN</b>\n\n🔗 Checking the link...\n⏳ Please wait...",
        "scan_analysis": "🛡️ <b>ANTI-PHISH GUARD</b>\n\n🔍 Analyzing the link...\n🌐 Looking up server information...",
        "scan_detected": "🚨 <b>THREAT DETECTED</b>\n\n❌ A dangerous link was detected!\n🛑 Blocking the message...",
        "apk_scan": "🔎 <b>SECURITY SCAN</b>\n\n📦 Checking the APK file...\n⏳ Please wait...",
        "apk_analysis": "🛡️ <b>ANTI-PHISH GUARD</b>\n\n🔍 Analyzing the APK file...\n⚠️ Security checks are in progress...",
        "apk_detected": "🚨 <b>THREAT DETECTED</b>\n\n❌ A potentially dangerous APK was detected!\n🛑 Blocking the file...",
        "apk_blocked": "🚨 <b>WARNING! THREAT DETECTED!</b>\n\n📦 <b>APK FILE BLOCKED!</b>\n\n👤 User: {user}\n🔴 Status: <b>BLOCKED</b>\n📱 Type: ANDROID APK\n\n⚠️ The file was removed from the group for security reasons.\n\n🛡️ <b>AntiPhish Guard</b>",
        "daily_video_title": "🇺🇿 <b>CYBERSECURITY VIDEO OF THE DAY</b>",
        "daily_video_description": "🛡️ A useful Uzbek-language video about cybersecurity and staying safe online.",
        "watch_video": "▶️ Watch video",
        "no_video": "❌ No trusted Uzbek-language cybersecurity video was found right now.",
        "guide_text": "📖 <b>APG guide</b>\n\n1️⃣ Add APG to your group.\n2️⃣ Make the bot an administrator.\n3️⃣ Grant permission to delete messages.\n4️⃣ Turn off Group Privacy.\n\nAPG can then inspect messages in the group.",
        "protection_text": "🛡️ <b>APG protection</b>\n\n🔗 URL scanning — ON\n🚨 Phishing detection — ON\n📦 APK protection — ON\n🗑️ Dangerous-message deletion — ON\n📊 Incident logging — ON\n\nProtection is managed separately for each group.",
    },
}

LANGUAGE_NAMES = {
    "uz": "🇺🇿 O‘zbek tili",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}

def init_language_db():
    """Create language preferences table without changing existing tables."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS language_preferences (
                scope TEXT NOT NULL,
                scope_id INTEGER NOT NULL,
                language TEXT NOT NULL DEFAULT 'uz',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (scope, scope_id)
            )
        """)

def set_language(scope: str, scope_id: int, language: str):
    if language not in SUPPORTED_LANGUAGES:
        language = "uz"
    init_language_db()
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO language_preferences (scope, scope_id, language, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(scope, scope_id) DO UPDATE SET
                language = excluded.language,
                updated_at = CURRENT_TIMESTAMP
        """, (scope, int(scope_id), language))

def get_language(scope: str, scope_id: int) -> str:
    if not scope_id:
        return "uz"
    init_language_db()
    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute(
            "SELECT language FROM language_preferences WHERE scope=? AND scope_id=?",
            (scope, int(scope_id))
        ).fetchone()
    return row[0] if row and row[0] in SUPPORTED_LANGUAGES else "uz"

def language_for_update(update) -> str:
    """Use group language in groups, otherwise the user's personal preference."""
    chat = getattr(update, "effective_chat", None)
    user = getattr(update, "effective_user", None)
    if chat and chat.type in ("group", "supergroup"):
        return get_language("chat", chat.id)
    if user:
        return get_language("user", user.id)
    return "uz"

def tr(language: str, key: str, **kwargs) -> str:
    language = language if language in SUPPORTED_LANGUAGES else "uz"
    template = TEXTS.get(language, TEXTS["uz"]).get(key, TEXTS["uz"].get(key, key))
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError):
        return template

def language_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇺🇿 O‘zbek", callback_data="setlang:uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang:ru"),
            InlineKeyboardButton("🇬🇧 English", callback_data="setlang:en"),
        ],
        [InlineKeyboardButton("⬅️ Menu / Меню / Menyu", callback_data="home")]
    ])

def language_button_row(language: str):
    return [InlineKeyboardButton(tr(language, "language_menu"), callback_data="language")]

def language_selection_text():
    # Language selector itself is intentionally multilingual.
    return (
        "🌍 <b>Tilni tanlang / Выберите язык / Choose a language</b>\n\n"
        "🇺🇿 O‘zbek tili\n🇷🇺 Русский язык\n🇬🇧 English"
    )
