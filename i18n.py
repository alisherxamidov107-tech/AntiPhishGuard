import sqlite3

DB_NAME = "database.db"

SUPPORTED_LANGUAGES = {
    "uz": "🇺🇿 O‘zbekcha",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}

TEXTS = {
    "uz": {
        "start": "🛡️ AntiPhish Guard botiga xush kelibsiz!\n\nMen fishing havolalari va internet firibgarligini aniqlashga yordam beraman.",
        "add_group": "➕ Guruhga qo‘shish",
        "guide": "📘 Qo‘llanma",
        "protection": "🛡️ Himoya",
        "statistics": "📊 Statistika",
        "language_menu": "🌐 Tilni o‘zgartirish",
        "language_title": "🌐 Kerakli tilni tanlang:",
        "language_saved": "✅ Til muvaffaqiyatli o‘zgartirildi!",
        "start_choose": "👇 Davom etish uchun /start buyrug‘ini yuboring.",
        "home": "🏠 Asosiy menyu",
        "back": "⬅️ Orqaga",
        "unknown": "❓ Noma’lum buyruq. /start buyrug‘ini yuboring.",
        "group_only": "⚠️ Bu buyruqni guruh ichida ishlating.",
        "protect_on": "✅ Guruh himoyasi yoqildi.",
        "protect_off": "🔕 Guruh himoyasi o‘chirildi.",
        "protected": "🛡️ Guruh himoyasi faol.",
        "not_protected": "🔕 Guruh himoyasi faol emas.",
        # --- scanner ---
        "scan_title": "🔎 <b>SECURITY SCAN</b>\n\n🔗 Havola tekshirilmoqda...\n⏳ Iltimos kuting...",
        "apk_title": "🔎 <b>SECURITY SCAN</b>\n\n📦 APK fayl tekshirilmoqda...\n⏳ Iltimos kuting...",
        "apk_blocked": "🚨 <b>APK FAYL BLOKLANDI!</b>\n\n👤 Foydalanuvchi: {user}\n🔴 Status: <b>BLOKLANDI</b>\n📱 Turi: ANDROID APK\n\n⚠️ Fayl xavfsizlik sababli o‘chirildi.\n\n🛡️ <b>AntiPhish Guard</b>",
        "phishing_blocked": "🚨 <b>XAVFLI LINK ANIQLANDI!</b>\n\n👤 Foydalanuvchi: {user}\n🔴 Status: <b>BLOKLANDI</b>\n⚠️ Risk: <b>PHISHING</b>\n\n{details}\n\n🚫 <b>BU HAVOLAGA KIRMANG!</b>\nXabar xavfsizlik sababli o‘chirildi.\n\n🛡️ <b>AntiPhish Guard</b>",
        "link_analysis": "🔎 <b>LINK TAHLILI</b>",
        "link": "🔗 Link",
        "domain": "🌐 Domen",
        "server_ip": "📡 Server IP",
        "country": "🌍 Davlat",
        "city": "🏙 Taxminiy shahar",
        "isp": "🏢 ISP/Hosting",
        "approx_location": "ℹ️ <i>Joylashuv IP bo‘yicha taxminiy.</i>",
        "not_found": "Aniqlanmadi",
        "ip_failed": "❌ Server IP ma'lumotini aniqlab bo‘lmadi.",
        "verdict_safe": "✅ Natija: shubhali belgilar topilmadi.",
        "verdict_danger": "🚨 Natija: <b>PHISHING EHTIMOLI YUQORI</b>",
        "no_video": "❌ Hozircha ishonchli o‘zbekcha kiberxavfsizlik videosi topilmadi.",
    },
    "ru": {
        "start": "🛡️ Добро пожаловать в AntiPhish Guard!\n\nЯ помогаю обнаруживать фишинговые ссылки и интернет-мошенничество.",
        "add_group": "➕ Добавить в группу",
        "guide": "📘 Инструкция",
        "protection": "🛡️ Защита",
        "statistics": "📊 Статистика",
        "language_menu": "🌐 Изменить язык",
        "language_title": "🌐 Выберите язык:",
        "language_saved": "✅ Язык успешно изменён!",
        "start_choose": "👇 Отправьте /start, чтобы продолжить.",
        "home": "🏠 Главное меню",
        "back": "⬅️ Назад",
        "unknown": "❓ Неизвестная команда. Отправьте /start.",
        "group_only": "⚠️ Используйте эту команду в группе.",
        "protect_on": "✅ Защита группы включена.",
        "protect_off": "🔕 Защита группы выключена.",
        "protected": "🛡️ Защита группы активна.",
        "not_protected": "🔕 Защита группы не активна.",
        "scan_title": "🔎 <b>SECURITY SCAN</b>\n\n🔗 Проверка ссылки...\n⏳ Пожалуйста, подождите...",
        "apk_title": "🔎 <b>SECURITY SCAN</b>\n\n📦 Проверка APK файла...\n⏳ Пожалуйста, подождите...",
        "apk_blocked": "🚨 <b>APK ФАЙЛ ЗАБЛОКИРОВАН!</b>\n\n👤 Пользователь: {user}\n🔴 Статус: <b>ЗАБЛОКИРОВАНО</b>\n📱 Тип: ANDROID APK\n\n⚠️ Файл удалён из соображений безопасности.\n\n🛡️ <b>AntiPhish Guard</b>",
        "phishing_blocked": "🚨 <b>ОПАСНАЯ ССЫЛКА ОБНАРУЖЕНА!</b>\n\n👤 Пользователь: {user}\n🔴 Статус: <b>ЗАБЛОКИРОВАНО</b>\n⚠️ Риск: <b>ФИШИНГ</b>\n\n{details}\n\n🚫 <b>НЕ ПЕРЕХОДИТЕ ПО ЭТОЙ ССЫЛКЕ!</b>\nСообщение удалено из соображений безопасности.\n\n🛡️ <b>AntiPhish Guard</b>",
        "link_analysis": "🔎 <b>АНАЛИЗ ССЫЛКИ</b>",
        "link": "🔗 Ссылка",
        "domain": "🌐 Домен",
        "server_ip": "📡 IP сервера",
        "country": "🌍 Страна",
        "city": "🏙 Примерный город",
        "isp": "🏢 ISP/Хостинг",
        "approx_location": "ℹ️ <i>Местоположение приблизительное, по IP.</i>",
        "not_found": "Не определено",
        "ip_failed": "❌ Не удалось определить IP сервера.",
        "verdict_safe": "✅ Результат: подозрительных признаков не найдено.",
        "verdict_danger": "🚨 Результат: <b>ВЫСОКАЯ ВЕРОЯТНОСТЬ ФИШИНГА</b>",
        "no_video": "❌ Пока не найдено надёжного видео по кибербезопасности.",
    },
    "en": {
        "start": "🛡️ Welcome to AntiPhish Guard!\n\nI help detect phishing links and online scams.",
        "add_group": "➕ Add to Group",
        "guide": "📘 Guide",
        "protection": "🛡️ Protection",
        "statistics": "📊 Statistics",
        "language_menu": "🌐 Change Language",
        "language_title": "🌐 Select your language:",
        "language_saved": "✅ Language changed successfully!",
        "start_choose": "👇 Send /start to continue.",
        "home": "🏠 Main Menu",
        "back": "⬅️ Back",
        "unknown": "❓ Unknown command. Send /start.",
        "group_only": "⚠️ Use this command inside a group.",
        "protect_on": "✅ Group protection enabled.",
        "protect_off": "🔕 Group protection disabled.",
        "protected": "🛡️ Group protection is active.",
        "not_protected": "🔕 Group protection is inactive.",
        "scan_title": "🔎 <b>SECURITY SCAN</b>\n\n🔗 Scanning link...\n⏳ Please wait...",
        "apk_title": "🔎 <b>SECURITY SCAN</b>\n\n📦 Scanning APK file...\n⏳ Please wait...",
        "apk_blocked": "🚨 <b>APK FILE BLOCKED!</b>\n\n👤 User: {user}\n🔴 Status: <b>BLOCKED</b>\n📱 Type: ANDROID APK\n\n⚠️ The file was deleted for security reasons.\n\n🛡️ <b>AntiPhish Guard</b>",
        "phishing_blocked": "🚨 <b>DANGEROUS LINK DETECTED!</b>\n\n👤 User: {user}\n🔴 Status: <b>BLOCKED</b>\n⚠️ Risk: <b>PHISHING</b>\n\n{details}\n\n🚫 <b>DO NOT OPEN THIS LINK!</b>\nThe message was deleted for security reasons.\n\n🛡️ <b>AntiPhish Guard</b>",
        "link_analysis": "🔎 <b>LINK ANALYSIS</b>",
        "link": "🔗 Link",
        "domain": "🌐 Domain",
        "server_ip": "📡 Server IP",
        "country": "🌍 Country",
        "city": "🏙 Approx. city",
        "isp": "🏢 ISP/Hosting",
        "approx_location": "ℹ️ <i>Location is approximate, based on IP.</i>",
        "not_found": "Unknown",
        "ip_failed": "❌ Could not determine server IP.",
        "verdict_safe": "✅ Result: no suspicious signs found.",
        "verdict_danger": "🚨 Result: <b>HIGH PHISHING PROBABILITY</b>",
        "no_video": "❌ No reliable cybersecurity video found right now.",
    },
}


def init_language_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS language_preferences (
                scope TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'uz',
                PRIMARY KEY (scope, scope_id)
            )
        """)
        conn.commit()


def set_language(scope, scope_id, language):
    if language not in SUPPORTED_LANGUAGES:
        language = "uz"

    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO language_preferences (scope, scope_id, language)
            VALUES (?, ?, ?)
            ON CONFLICT(scope, scope_id)
            DO UPDATE SET language = excluded.language
        """, (scope, str(scope_id), language))
        conn.commit()


def get_language(scope, scope_id):
    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute("""
            SELECT language FROM language_preferences
            WHERE scope = ? AND scope_id = ?
        """, (scope, str(scope_id))).fetchone()

    if row and row[0] in SUPPORTED_LANGUAGES:
        return row[0]
    return "uz"


def language_for_update(update):
    chat = update.effective_chat
    user = update.effective_user

    if chat and chat.type in ("group", "supergroup"):
        return get_language("chat", chat.id)

    if user:
        return get_language("user", user.id)

    return "uz"


def tr(language, key, **kwargs):
    if language not in TEXTS:
        language = "uz"

    text = TEXTS[language].get(key) or TEXTS["uz"].get(key, key)

    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def language_selection_text():
    return "🌐 <b>Tilni tanlang / Выберите язык / Select language</b>"


def language_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 O‘zbekcha", callback_data="setlang:uz")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang:ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="setlang:en")],
    ])
