from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [item.strip() for item in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if item.strip()]

INSTALLED_APPS = [
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.drawing_metadata",
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

ROOT_URLCONF = "knowledge_system_backend.urls"

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

WSGI_APPLICATION = "knowledge_system_backend.wsgi.application"
ASGI_APPLICATION = "knowledge_system_backend.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("DJANGO_SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
    }
}

AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = []

LANGUAGE_CODE = "ja-jp"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ]
}

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    ).split(",")
    if origin.strip()
]

DRAWING_METADATA_STORAGE_ROOT = Path(
    os.getenv("DRAWING_METADATA_STORAGE_ROOT", str(BASE_DIR / "var" / "drawing_metadata"))
)
DRAWING_METADATA_PREVIEW_ASSET_ROOT = Path(
    os.getenv("DRAWING_METADATA_PREVIEW_ASSET_ROOT", str(DRAWING_METADATA_STORAGE_ROOT / "preview_assets"))
)
DRAWING_METADATA_PREVIEW_ASSET_BASE_URL = os.getenv(
    "DRAWING_METADATA_PREVIEW_ASSET_BASE_URL", "/api/v1/drawing-metadata-preview-assets"
).strip()
DRAWING_METADATA_HANDOFF_MANIFEST = os.getenv(
    "DRAWING_METADATA_HANDOFF_MANIFEST",
    str(BASE_DIR.parent / "output" / "souya_handoff" / "icad_extract_import_manifest_all_shared_2026-07-15.json"),
).strip()
DRAWING_METADATA_EXTRACTOR_EXECUTABLE = os.getenv("DRAWING_METADATA_EXTRACTOR_EXECUTABLE", "").strip()
DRAWING_METADATA_SXNET_DLL_PATH = os.getenv("DRAWING_METADATA_SXNET_DLL_PATH", "").strip()
DRAWING_METADATA_ICAD_EXECUTABLE = os.getenv("DRAWING_METADATA_ICAD_EXECUTABLE", "").strip()
DRAWING_METADATA_ICAD_STARTUP_WAIT_SECONDS = int(os.getenv("DRAWING_METADATA_ICAD_STARTUP_WAIT_SECONDS", "8"))
DRAWING_METADATA_ICAD_SHUTDOWN_IF_AUTOSTARTED = (
    os.getenv("DRAWING_METADATA_ICAD_SHUTDOWN_IF_AUTOSTARTED", "true").lower() == "true"
)
DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS = int(os.getenv("DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS", "60"))
DRAWING_METADATA_WORKER_POLL_SECONDS = int(os.getenv("DRAWING_METADATA_WORKER_POLL_SECONDS", "5"))
DRAWING_METADATA_JOB_LEASE_SECONDS = int(os.getenv("DRAWING_METADATA_JOB_LEASE_SECONDS", "180"))
DRAWING_METADATA_LLM_PROVIDER = os.getenv("DRAWING_METADATA_LLM_PROVIDER", "gemini").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()
GEMINI_FALLBACK_MODELS = [
    model.strip()
    for model in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.1-flash-lite,gemini-3.5-flash").split(",")
    if model.strip()
]
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.0"))
DRAWING_METADATA_SCHEMA_VERSION = "1.0.0"
DRAWING_METADATA_NORMALIZER_VERSION = "1.0.0"
DRAWING_METADATA_TAG_RULE_VERSION = "1.0.0"
