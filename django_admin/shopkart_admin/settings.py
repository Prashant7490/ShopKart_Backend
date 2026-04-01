"""
ShopKart Django Admin Settings
Sirf admin panel ke liye - FastAPI ka data same DB se read karega
"""
from pathlib import Path

# Django admin ka BASE_DIR = django_admin/ folder
BASE_DIR = Path(__file__).resolve().parent.parent

# FastAPI wali DB ka path (ek level upar)
FASTAPI_ROOT = BASE_DIR.parent

SECRET_KEY = 'django-shopkart-admin-secret-key-xyz-change-in-prod'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'store',
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

ROOT_URLCONF = 'shopkart_admin.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'shopkart_admin.wsgi.application'

# ✅ Same SQLite DB jo FastAPI use kar raha hai
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': FASTAPI_ROOT / 'shopkart.db',
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = False   # FastAPI bhi timezone-naive use karta hai

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'prashantmishra7649@gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'prashantmishra7649@gmail.com'
# EMAIL_HOST_PASSWORD = 'wvas aplh vxve ytor'


SMTP_USER = "prashantmishra7649@gmail.com"
SMTP_PASSWORD = "wvas aplh vxve ytor"
FROM_EMAIL = "ShopKart <prashantmishra7649@gmail.com>"
EMAIL_ENABLED = True