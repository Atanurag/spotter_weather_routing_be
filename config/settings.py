
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-only-change-me",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1",
    ).split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "corsheaders",
    "api",
]

WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": "048c7cd433104c46c66f8b527cf7330ce6ded454a5972b7486d669d13b600d14dbb1b82e7c20bd18ce77e9132b4f42ceb9c4f7476557613aa8d17131e71d42f181",
    "VAPID_PRIVATE_KEY": "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgYpF27+HbPkRebcoFUbqqLD6EJXozS81zh/tWj/ZhOQahRANCAASMfNQzEExGxm+LUnz3Mwzm3tRUpZcrdIbWadE7YA0U27G4LnwgvRjOd+kTK09CzrnE90dlV2E6qNFxMecdQvGB",
    "VAPID_ADMIN_EMAIL": "mailto:anurag@iotronsys.com",
}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = []
WSGI_APPLICATION = "config.wsgi.application"

# settings.py

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        (
            "http://localhost:5173,"
            "http://127.0.0.1:5173,"
            "https://spotter-weather-routing-fe.vercel.app,"
            "https://demo-dashboard-gray.vercel.app,"
        ),
    ).split(",")
    if origin.strip()
]
