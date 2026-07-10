import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-0(y0o9u=ml@n6&i^qcpn0b)ad41#eotn-+@*@loo+v=+%gk-ne'

DEBUG = True

ALLOWED_HOSTS = ['*', 'render.com']


INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    "cloudinary",
    "cloudinary_storage",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bill_management.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'bill_management.wsgi.application'

import os
import dj_database_url
import cloudinary

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL")
    )
}


CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.environ.get("hrwgb0ik"),
    "API_KEY": os.environ.get("496472468144582"),
    "API_SECRET": os.environ.get("BQMQOSH7jaOhiOR3nABteN7U0NY"),
    "SECURE": True,
}

cloudinary.config(
    cloud_name=os.environ.get("hrwgb0ik"),
    api_key=os.environ.get("496472468144582"),
    api_secret=os.environ.get("BQMQOSH7jaOhiOR3nABteN7U0NY"),
    secure=True,
)

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'bill_create'
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = 'home'

# WeasyPrint configuration
WEASYPRINT_BASEURL = 'http://localhost:8000'

# Font configuration
FONT_CONFIG = {
    'font_family': 'BanglaFont',
    'fallback_fonts': ['SolaimanLipi', 'Kalpurush', 'Arial', 'sans-serif']
}


JAZZMIN_SETTINGS = {
    # ── Branding ───────────────────────────────────────────────
    "site_title": "BillM Admin",
    "site_header": "বিল ম্যানেজমেন্ট",
    "site_brand": "BillM",
    "site_logo": None,
    "login_logo": None,
    "login_logo_dark": None,
    "site_logo_classes": "img-circle",
    "site_icon": None,
    "welcome_sign": "বিল ম্যানেজমেন্ট সিস্টেমে স্বাগতম",
    "copyright": "BillM © 2026",
    "search_model": ["auth.user", "core.Bill"],
    "user_avatar": None,

    # ── Top Menu ───────────────────────────────────────────────
    "topmenu_links": [
        {"name": "হোম",        "url": "/",             "new_window": False},
        {"name": "বিল স্ট্যাটাস", "url": "/bill-status/", "new_window": False},
        {"name": "সব বিল",     "url": "/all-bills/",   "new_window": False},
        {"model": "auth.User"},
        {"app": "core"},
    ],

    # ── User Menu ──────────────────────────────────────────────
    "usermenu_links": [
        {"name": "সাইট দেখুন", "url": "/", "new_window": False, "icon": "fas fa-home"},
        {"model": "auth.user"},
    ],

    # ── Sidebar ────────────────────────────────────────────────
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],

    "order_with_respect_to": [
        "auth",
        "core",
        "core.Bill",
        "core.Task",
        "core.WorkType",
        "core.Benefit",
        "core.Profile",
        "core.SliderImage",
        "core.ActivityLog",
    ],

    "icons": {
        "auth":               "fas fa-users-cog",
        "auth.user":          "fas fa-user",
        "auth.Group":         "fas fa-users",
        "core.Bill":          "fas fa-file-invoice-dollar",
        "core.Task":          "fas fa-tasks",
        "core.WorkType":      "fas fa-briefcase",
        "core.Benefit":       "fas fa-coins",
        "core.Profile":       "fas fa-id-card",
        "core.SliderImage":   "fas fa-images",
        "core.ActivityLog":   "fas fa-history",
        "core.SystemSetting": "fas fa-cogs",
    },
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-circle",

    # ── UI Tweaks ──────────────────────────────────────────────
    "related_modal_active": True,
    "custom_css": "admin/css/admin_custom.css",   # ← single, correct path
    "custom_js": None,
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "auth.user":  "collapsible",
        "auth.group": "vertical_tabs",
    },
    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-success",
    "accent": "accent-teal",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-teal",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "darkly",
    # "dark_mode_theme": "darkly",  ← REMOVED (deprecated, causes warning)
    "default_theme_mode": "dark",   # ← NEW replacement
    "button_classes": {
        "primary":   "btn-primary",
        "secondary": "btn-secondary",
        "info":      "btn-info",
        "warning":   "btn-warning",
        "danger":    "btn-danger",
        "success":   "btn-success",
    },
    "actions_sticky_top": True,
}


# Session settings for "Remember Me" functionality
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Don't expire when browser closes
SESSION_COOKIE_AGE = 3 * 24 * 60 * 60  # 3 days in seconds (259200 seconds)
SESSION_SAVE_EVERY_REQUEST = True  # Refresh session expiry on each request
