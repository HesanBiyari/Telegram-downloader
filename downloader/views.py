import os
import uuid
import threading
from urllib.parse import urlparse

from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.shortcuts import render, redirect

from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
)

from telegram_client import get_client


# =========================================================
# DOWNLOAD STORAGE
# =========================================================

DOWNLOADS = {}


# =========================================================
# TELEGRAM SESSION
# =========================================================

def get_session_name(request):
    """
    برای هر Session مرورگر یک Telegram session جدا می‌سازیم.
    """

    if "telegram_session" not in request.session:
        request.session["telegram_session"] = uuid.uuid4().hex
        request.session.save()

    return request.session["telegram_session"]


# =========================================================
# LOGIN
# =========================================================

def login_page(request):

    if request.method == "POST":

        phone = request.POST.get("phone", "").strip()

        if not phone:
            return render(
                request,
                "downloader/login.html",
                {
                    "error": "شماره تلفن را وارد کنید."
                }
            )

        session_name = get_session_name(request)

        client = get_client(session_name)

        try:

            client.connect()

            result = client.send_code_request(phone)

            request.session["telegram_phone"] = phone

            request.session["phone_code_hash"] = (
                result.phone_code_hash
            )

            request.session.save()

            return redirect("verify")

        except PhoneNumberInvalidError:

            return render(
                request,
                "downloader/login.html",
                {
                    "error": "شماره تلفن معتبر نیست."
                }
            )

        except Exception as e:

            return render(
                request,
                "downloader/login.html",
                {
                    "error": str(e)
                }
            )

        finally:

            try:

                if client.is_connected():
                    client.disconnect()

            except Exception:
                pass

    return render(
        request,
        "downloader/login.html"
    )


# =========================================================
# VERIFY CODE
# =========================================================

def verify(request):

    phone = request.session.get(
        "telegram_phone"
    )

    if not phone:
        return redirect("login")

    if request.method == "POST":

        code = request.POST.get(
            "code",
            ""
        ).strip()

        if not code:

            return render(
                request,
                "downloader/verify.html",
                {
                    "error": "کد ورود را وارد کنید."
                }
            )

        session_name = get_session_name(request)

        client = get_client(session_name)

        try:

            client.connect()

            client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=request.session.get(
                    "phone_code_hash"
                )
            )

            request.session["telegram_logged_in"] = True

            request.session.save()

            return redirect("home")

        except SessionPasswordNeededError:

            return redirect("password")

        except PhoneCodeInvalidError:

            return render(
                request,
                "downloader/verify.html",
                {
                    "error": "کد واردشده اشتباه است."
                }
            )

        except Exception as e:

            return render(
                request,
                "downloader/verify.html",
                {
                    "error": str(e)
                }
            )

        finally:

            try:

                if client.is_connected():
                    client.disconnect()

            except Exception:
                pass

    return render(
        request,
        "downloader/verify.html"
    )


# =========================================================
# 2FA PASSWORD
# =========================================================

def password(request):

    phone = request.session.get(
        "telegram_phone"
    )

    if not phone:
        return redirect("login")

    if request.method == "POST":

        password_value = request.POST.get(
            "password",
            ""
        )

        if not password_value:

            return render(
                request,
                "downloader/password.html",
                {
                    "error": "رمز دو مرحله‌ای را وارد کنید."
                }
            )

        session_name = get_session_name(request)

        client = get_client(session_name)

        try:

            client.connect()

            client.sign_in(
                password=password_value
            )

            request.session["telegram_logged_in"] = True

            request.session.save()

            return redirect("home")

        except Exception as e:

            return render(
                request,
                "downloader/password.html",
                {
                    "error": str(e)
                }
            )

        finally:

            try:

                if client.is_connected():
                    client.disconnect()

            except Exception:
                pass

    return render(
        request,
        "downloader/password.html"
    )


# =========================================================
# PARSE TELEGRAM LINK
# =========================================================

def parse_telegram_link(link):

    link = link.strip()

    if not link:
        raise ValueError(
            "لینک خالی است."
        )

    parsed = urlparse(link)

    if parsed.scheme not in (
        "http",
        "https"
    ):
        raise ValueError(
            "لینک باید با https:// یا http:// شروع شود."
        )

    if parsed.netloc.lower() not in (
        "t.me",
        "www.t.me",
        "telegram.me",
        "www.telegram.me",
    ):
        raise ValueError(
            "این لینک، لینک معتبر Telegram نیست."
        )

    parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if len(parts) < 2:

        raise ValueError(
            "فرمت لینک باید شبیه "
            "https://t.me/channel/123 باشد."
        )

    username = parts[0]

    try:

        message_id = int(parts[1])

    except ValueError:

        raise ValueError(
            "شماره پیام در لینک معتبر نیست."
        )

    return username, message_id


# =========================================================
# HOME
# =========================================================

def home(request):

    logged_in = request.session.get(
        "telegram_logged_in",
        False
    )

    if not logged_in:

        return render(
            request,
            "downloader/home.html",
            {
                "logged_in": False
            }
        )

    # -----------------------------------------------------
    # CHECK TELEGRAM LINK
    # -----------------------------------------------------

    if request.method == "POST":

        link = request.POST.get(
            "telegram_url",
            ""
        ).strip()

        if not link:

            return render(
                request,
                "downloader/home.html",
                {
                    "logged_in": True,
                    "error": "لینک را وارد کنید."
                }
            )

        client = None

        try:

            username, message_id = (
                parse_telegram_link(link)
            )

            session_name = get_session_name(
                request
            )

            client = get_client(
                session_name
            )

            client.connect()

            entity = client.get_entity(
                username
            )

            message = client.get_messages(
                entity,
                ids=message_id
            )

            if not message:

                raise ValueError(
                    "پیام پیدا نشد."
                )

            if not message.media:

                raise ValueError(
                    "این پیام فایل قابل دانلود ندارد."
                )

            file_name = "Telegram File"

            file_size = 0

            file_type = "Unknown"

            if message.file:

                file_name = (
                    message.file.name
                    or "Telegram File"
                )

                file_size = (
                    message.file.size
                    or 0
                )

                file_type = (
                    message.file.mime_type
                    or "Unknown"
                )

            if file_size:

                size_mb = round(
                    file_size / (
                        1024 * 1024
                    ),
                    2
                )

                size_text = (
                    f"{size_mb} MB"
                )

            else:

                size_text = "نامشخص"

            # ذخیره لینک برای شروع دانلود
            request.session[
                "telegram_url"
            ] = link

            request.session.save()

            return render(
                request,
                "downloader/home.html",
                {
                    "logged_in": True,

                    "file_info": {
                        "name": file_name,
                        "size": size_text,
                        "type": file_type,
                    }
                }
            )

        except Exception as e:

            return render(
                request,
                "downloader/home.html",
                {
                    "logged_in": True,
                    "error": str(e)
                }
            )

        finally:

            if client:

                try:

                    if client.is_connected():
                        client.disconnect()

                except Exception:
                    pass

    return render(
        request,
        "downloader/home.html",
        {
            "logged_in": True
        }
    )


# =========================================================
# START DOWNLOAD
# =========================================================

def start_download(request):

    if not request.session.get(
        "telegram_logged_in",
        False
    ):

        return JsonResponse(
            {
                "error": "ابتدا وارد Telegram شوید."
            },
            status=401
        )

    link = request.session.get(
        "telegram_url"
    )

    if not link:

        return JsonResponse(
            {
                "error": "لینک دانلود پیدا نشد."
            },
            status=400
        )

    session_name = get_session_name(
        request
    )

    download_id = uuid.uuid4().hex

    DOWNLOADS[download_id] = {

        "status": "starting",

        "progress": 0,

        "downloaded": 0,

        "total": 0,

        "file_path": None,

        "error": None,

        "session_name": session_name,

    }

    thread = threading.Thread(

        target=download_file_background,

        args=(
            download_id,
            link,
            session_name,
        ),

        daemon=True,
    )

    thread.start()

    return JsonResponse(
        {
            "download_id": download_id
        }
    )


# =========================================================
# BACKGROUND DOWNLOAD
# =========================================================

def download_file_background(
    download_id,
    link,
    session_name
):

    client = None

    try:

        DOWNLOADS[download_id][
            "status"
        ] = "downloading"

        username, message_id = (
            parse_telegram_link(link)
        )

        client = get_client(
            session_name
        )

        client.connect()

        entity = client.get_entity(
            username
        )

        message = client.get_messages(
            entity,
            ids=message_id
        )

        if not message:

            raise ValueError(
                "پیام پیدا نشد."
            )

        if not message.media:

            raise ValueError(
                "این پیام فایل قابل دانلود ندارد."
            )

        downloads_dir = os.path.join(
            settings.BASE_DIR,
            "downloads"
        )

        os.makedirs(
            downloads_dir,
            exist_ok=True
        )

        # ---------------------------------------------
        # REAL TELETHON PROGRESS CALLBACK
        # ---------------------------------------------

        def progress_callback(
            downloaded,
            total
        ):

            percent = 0

            if total:

                percent = int(
                    downloaded * 100 / total
                )

            DOWNLOADS[
                download_id
            ].update({

                "progress": percent,

                "downloaded": downloaded,

                "total": total,

            })

        # ---------------------------------------------
        # DOWNLOAD
        # ---------------------------------------------

        file_path = client.download_media(

            message,

            file=downloads_dir,

            progress_callback=progress_callback,

        )

        if not file_path:

            raise ValueError(
                "دانلود فایل ناموفق بود."
            )

        DOWNLOADS[
            download_id
        ].update({

            "status": "completed",

            "progress": 100,

            "file_path": file_path,

        })

    except Exception as e:

        DOWNLOADS[
            download_id
        ].update({

            "status": "error",

            "error": str(e),

        })

    finally:

        if client:

            try:

                if client.is_connected():
                    client.disconnect()

            except Exception:
                pass


# =========================================================
# DOWNLOAD PROGRESS
# =========================================================

def download_progress(
    request,
    download_id
):

    download = DOWNLOADS.get(
        download_id
    )

    if not download:

        return JsonResponse(
            {
                "error": "دانلود پیدا نشد."
            },
            status=404
        )

    # فقط Session خودش بتواند دانلود خودش را ببیند
    session_name = get_session_name(
        request
    )

    if download.get(
        "session_name"
    ) != session_name:

        return JsonResponse(
            {
                "error": "دسترسی غیرمجاز."
            },
            status=403
        )

    return JsonResponse({

        "status": download[
            "status"
        ],

        "progress": download[
            "progress"
        ],

        "downloaded": download[
            "downloaded"
        ],

        "total": download[
            "total"
        ],

        "error": download[
            "error"
        ],

    })


# =========================================================
# GET DOWNLOADED FILE
# =========================================================

def download_file(
    request,
    download_id
):

    download = DOWNLOADS.get(
        download_id
    )

    if not download:

        return JsonResponse(
            {
                "error": "دانلود پیدا نشد."
            },
            status=404
        )

    session_name = get_session_name(
        request
    )

    if download.get(
        "session_name"
    ) != session_name:

        return JsonResponse(
            {
                "error": "دسترسی غیرمجاز."
            },
            status=403
        )

    if download["status"] != "completed":

        return JsonResponse(
            {
                "error": "دانلود هنوز کامل نشده است."
            },
            status=400
        )

    file_path = download.get(
        "file_path"
    )

    if not file_path or not os.path.exists(
        file_path
    ):

        return JsonResponse(
            {
                "error": "فایل پیدا نشد."
            },
            status=404
        )

    return FileResponse(

        open(file_path, "rb"),

        as_attachment=True,

        filename=os.path.basename(
            file_path
        ),

    )