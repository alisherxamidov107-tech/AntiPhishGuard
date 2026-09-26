import re
from urllib.parse import urlparse


SUSPICIOUS_WORDS = [
    "free-gift",
    "freegift",
    "verify-account",
    "verify-login",
    "secure-login",
    "claim-prize",
    "claim-reward",
    "wallet-connect",
    "crypto-gift",
    "telegram-gift",
    "login-verify",
]


URL_PATTERN = re.compile(
    r"(https?://[^\s]+|www\.[^\s]+)",
    re.IGNORECASE
)


def extract_urls(text: str):
    if not text:
        return []

    return URL_PATTERN.findall(text)


def check_url(url: str):
    clean_url = url.rstrip(".,!?;:)")

    if clean_url.startswith("www."):
        clean_url = "https://" + clean_url

    try:
        parsed = urlparse(clean_url)
        domain = parsed.netloc.lower()

        if not domain:
            return False

        # IP manzil orqali berilgan link
        if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", domain):
            return True

        full_url = clean_url.lower()

        # Shubhali so'zlarni tekshirish
        for word in SUSPICIOUS_WORDS:
            if word in full_url:
                return True

        suspicious_patterns = [
            "telegram-login",
            "tg-login",
            "telegram-auth",
            "password",
            "signin",
            "account-verify",
        ]

        for pattern in suspicious_patterns:
            if pattern in full_url:
                return True

        return False

    except Exception:
        return False


def scan_text(text: str):
    urls = extract_urls(text)

    dangerous_urls = []

    for url in urls:
        if check_url(url):
            dangerous_urls.append(url)

    return dangerous_urls