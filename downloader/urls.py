from django.urls import path

from . import views


urlpatterns = [

    # Home
    path(
        "",
        views.home,
        name="home"
    ),

    # Telegram Login
    path(
        "login/",
        views.login_page,
        name="login"
    ),

    # Telegram verification code
    path(
        "verify/",
        views.verify,
        name="verify"
    ),

    # Telegram 2FA
    path(
        "password/",
        views.password,
        name="password"
    ),

    # Start download
    path(
        "download/start/",
        views.start_download,
        name="start_download"
    ),

    # Real download progress
    path(
        "download/progress/<str:download_id>/",
        views.download_progress,
        name="download_progress"
    ),

    # Download completed file
    path(
        "download/file/<str:download_id>/",
        views.download_file,
        name="download_file"
    ),

]