import os

from django.conf import settings
from telethon.sync import TelegramClient


SESSIONS_DIR = os.path.join(
    settings.BASE_DIR,
    "sessions"
)

os.makedirs(
    SESSIONS_DIR,
    exist_ok=True
)


def get_client(session_name):

    session_path = os.path.join(
        SESSIONS_DIR,
        session_name
    )

    return TelegramClient(
        session_path,
        settings.API_ID,
        settings.API_HASH
    )