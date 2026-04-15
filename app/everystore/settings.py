import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Allow nginx reverse proxy
_admin_port = os.environ.get('ADMIN_PORT', '')

CSRF_TRUSTED_ORIGINS = [
    f'https://{h}' for h in ALLOWED_HOSTS if not h.startswith('.')
] + [
    f'http://{h}' for h in ALLOWED_HOSTS if not h.startswith('.')
]

# Admin panel runs on a non-standard port — must be explicitly trusted for CSRF
if _admin_port:
    for _h in ALLOWED_HOSTS:
        if not _h.startswith('.'):
            CSRF_TRUSTED_ORIGINS.append(f'https://{_h}:{_admin_port}')

INSTALLED_APPS = [
    # django-unfold must come before django.contrib.admin
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # project apps
    'store',
    'orders',
    'payments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'everystore.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.store_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'everystore.wsgi.application'

# ── Database (AWS RDS PostgreSQL) ─────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='everystore'),
        'USER': config('DB_USER', default='everystore'),
        'PASSWORD': config('DB_PASS'),
        'HOST': config('DB_HOST', default='everystore-db'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'sslmode': config('DB_SSLMODE', default='prefer'),
        },
        'CONN_MAX_AGE': 60,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_TZ = True

# ── Static files (WhiteNoise — served by Django/Gunicorn, cached by nginx) ────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# ── Media files (AWS S3) ──────────────────────────────────────────────────────
S3_BUCKET = config('S3_BUCKET', default='')

if S3_BUCKET:
    AWS_ACCESS_KEY_ID = config('S3_ACCESS_KEY')
    AWS_SECRET_ACCESS_KEY = config('S3_SECRET_KEY')
    AWS_STORAGE_BUCKET_NAME = S3_BUCKET
    AWS_S3_REGION_NAME = config('S3_REGION', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{S3_BUCKET}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
    AWS_DEFAULT_ACL = None             # rely on bucket policy for public access
    AWS_QUERYSTRING_AUTH = False       # clean, permanent URLs (no signing)
    AWS_S3_FILE_OVERWRITE = False      # never overwrite existing files
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}

    STORAGES = {
        'default': {'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
    }
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
    MEDIA_ROOT = ''
else:
    # Local development fallback
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
    }
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'mediafiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Admin ─────────────────────────────────────────────────────────────────────
ADMIN_URL_PATH = os.environ.get('ADMIN_URL_PATH', 'admin')

# Trust X-Forwarded-Proto from nginx
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=465, cast=int)
EMAIL_USE_SSL = config('EMAIL_PORT', default=465, cast=int) == 465
EMAIL_USE_TLS = not EMAIL_USE_SSL
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('EMAIL_FROM', default=config('EMAIL_HOST_USER', default=''))

# ── PayPal ────────────────────────────────────────────────────────────────────
PAYMENT_MODE = config('PAYMENT_MODE', default='sandbox')
PAYPAL_CLIENT_ID = config('PAYPAL_CLIENT_ID', default='')
PAYPAL_CLIENT_SECRET = config('PAYPAL_CLIENT_SECRET', default='')

# ── Store / Theme ─────────────────────────────────────────────────────────────
STORE_NAME = config('STORE_NAME', default='EveryStore')
STORE_CURRENCY = config('STORE_CURRENCY', default='USD')
SELLER_CONTACT_TYPE = config('SELLER_CONTACT_TYPE', default='email')
SELLER_CONTACT_VALUE = config('SELLER_CONTACT_VALUE', default='')
THEME_PRIMARY_COLOR = config('THEME_PRIMARY_COLOR', default='#6366f1')
THEME_LOGO_URL = config('THEME_LOGO_URL', default='')
THEME_HERO_IMAGE_URL = config('THEME_HERO_IMAGE_URL', default='')

# ── django-unfold admin theme ─────────────────────────────────────────────────
_ap = ADMIN_URL_PATH  # shorthand

UNFOLD = {
    "SITE_TITLE": STORE_NAME,
    "SITE_HEADER": f"{STORE_NAME} Admin",
    "SITE_SYMBOL": "storefront",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "primary": {
            "50": "238 242 255",
            "100": "224 231 255",
            "200": "199 210 254",
            "300": "165 180 252",
            "400": "129 140 248",
            "500": "99 102 241",
            "600": "79 70 229",
            "700": "67 56 202",
            "800": "55 48 163",
            "900": "49 46 129",
            "950": "30 27 75",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Store",
                "separator": True,
                "items": [
                    {"title": "Products", "icon": "inventory_2", "link": f"/{_ap}/store/product/"},
                    {"title": "Categories", "icon": "category", "link": f"/{_ap}/store/category/"},
                    {"title": "Product Images", "icon": "photo_library", "link": f"/{_ap}/store/productimage/"},
                ],
            },
            {
                "title": "Orders",
                "separator": True,
                "items": [
                    {"title": "Orders", "icon": "shopping_bag", "link": f"/{_ap}/orders/order/"},
                ],
            },
            {
                "title": "Settings",
                "separator": True,
                "items": [
                    {"title": "Site Settings", "icon": "settings", "link": f"/{_ap}/store/sitesettings/"},
                    {"title": "Users", "icon": "person", "link": f"/{_ap}/auth/user/"},
                ],
            },
        ],
    },
}
