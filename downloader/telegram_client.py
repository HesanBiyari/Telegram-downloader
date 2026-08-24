import os

from django.conf import settings
from telethon import TelegramClient


API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")


if not API_ID or not API_HASH:
    raise ValueError(
        "API_ID و API_HASH را تنظیم کنید."
    )


def get_client(session_name):
    """
    ساخت TelegramClient برای یک session مشخص.
    """

    sessions_dir = os.path.join(
        settings.BASE_DIR,
        "telegram_sessions"
    )

    os.makedirs(
        sessions_dir,
        exist_ok=True
    )

    session_path = os.path.join(
        sessions_dir,
        session_name
    )

    return TelegramClient(
        session_path,
        API_ID,
        API_HASH
    )