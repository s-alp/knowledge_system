from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

INSTALLED_APPS = [
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.viewer",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "viewer_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "viewer_backend.wsgi.application"
ASGI_APPLICATION = "viewer_backend.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("DJANGO_SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "ja-jp"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ]
}

VIEWER_TIMEOUT_SECONDS = int(os.getenv("VIEWER_TIMEOUT_SECONDS", "15"))
VIEWER_MAX_DOWNLOAD_BYTES = int(os.getenv("VIEWER_MAX_DOWNLOAD_BYTES", str(30 * 1024 * 1024)))
VIEWER_ARTIFACT_TTL_SECONDS = int(os.getenv("VIEWER_ARTIFACT_TTL_SECONDS", str(24 * 60 * 60)))
VIEWER_ALLOWED_SCHEMES = tuple(os.getenv("VIEWER_ALLOWED_SCHEMES", "http,https").split(","))
VIEWER_INTERNAL_URLS_ENABLED = os.getenv("VIEWER_INTERNAL_URLS_ENABLED", "true").lower() == "true"
VIEWER_INTERNAL_HOST_ALLOWLIST = tuple(
    item.strip().lower()
    for item in os.getenv(
        "VIEWER_INTERNAL_HOST_ALLOWLIST",
        "fileserver.example.local,viewer-demo.internal",
    ).split(",")
    if item.strip()
)
VIEWER_INTERNAL_CIDR_ALLOWLIST = tuple(
    item.strip()
    for item in os.getenv(
        "VIEWER_INTERNAL_CIDR_ALLOWLIST",
        "10.10.0.0/16,192.168.100.0/24",
    ).split(",")
    if item.strip()
)
VIEWER_STEP_ENABLED = os.getenv("VIEWER_STEP_ENABLED", "true").lower() == "true"
VIEWER_LOCAL_FILE_ENABLED = os.getenv("VIEWER_LOCAL_FILE_ENABLED", "false").lower() == "true"
VIEWER_STORAGE_ROOT = Path(os.getenv("VIEWER_STORAGE_ROOT", str(MEDIA_ROOT / "viewer")))
VIEWER_STEP_STL_TOLERANCE = float(os.getenv("VIEWER_STEP_STL_TOLERANCE", "0.8"))
VIEWER_STEP_STL_ANGULAR_TOLERANCE = float(os.getenv("VIEWER_STEP_STL_ANGULAR_TOLERANCE", "0.4"))
PDM_API_BASE_URL = os.getenv("PDM_API_BASE_URL", "").strip()
PDM_DRAWING_RESOLVE_PATH_TEMPLATE = os.getenv(
    "PDM_DRAWING_RESOLVE_PATH_TEMPLATE",
    "/drawings/internals/{drawing_id}/",
)
PDM_REQUEST_TIMEOUT_SECONDS = int(os.getenv("PDM_REQUEST_TIMEOUT_SECONDS", "15"))
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173,http://localhost:4173",
    ).split(",")
    if origin.strip()
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"structured": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        }
    },
    "loggers": {
        "apps.viewer": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        }
    },
}
