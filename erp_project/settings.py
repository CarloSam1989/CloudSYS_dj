import os
from pathlib import Path
import environ



# 1. CONFIGURACIÓN INICIAL Y DE ENTORNO
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
AUTH_USER_MODEL = 'core.Usuario'
env = environ.Env(
    # Valores por defecto y tipo de dato
    DEBUG=(bool, False)
)

# Lee el archivo .env (solo para desarrollo local)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


# 2. VARIABLES DE SEGURIDAD Y DEPLOYMENT
# ==============================================================================
# Leídas desde el entorno. NUNCA las escribas directamente aquí.
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# 3. APLICACIONES Y MIDDLEWARE
# ==============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Para servir archivos estáticos
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# 4. CONFIGURACIÓN DEL PROYECTO (URLs, WSGI)
# ==============================================================================
ROOT_URLCONF = 'erp_project.urls'
WSGI_APPLICATION = 'erp_project.wsgi.application'


# 5. PLANTILLAS (TEMPLATES)
# ==============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# 6. BASE DE DATOS
# ==============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),         
        'PASSWORD': env('DB_PASSWORD'), 
        'HOST': env('DB_HOST'),         
        'PORT': env('DB_PORT'),
    }
}

# 7. VALIDACIÓN DE CONTRASEÑAS Y AUTENTICACIÓN
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LOGIN_URL = 'login'


# 8. INTERNACIONALIZACIÓN
# ==============================================================================
LANGUAGE_CODE = 'es-ec' # Español de Ecuador
TIME_ZONE = 'America/Guayaquil'
USE_I18N = True
USE_TZ = True


# 9. ARCHIVOS ESTÁTICOS (CSS, JS, Imágenes)
# ==============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = (os.path.join(BASE_DIR, 'static'),)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# 10. CONFIGURACIÓN DE CELERY
# ==============================================================================
CELERY_BROKER_URL = env('REDIS_URL')
CELERY_RESULT_BACKEND = env('REDIS_URL')

# Opcional: Evita que Celery se queje si no hay URL configurada durante el build
if not CELERY_BROKER_URL:
    print("ADVERTENCIA: Celery no está configurado. Las tareas asíncronas fallarán.")

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 11. CONFIGURACIÓN DE CORREO
# ==============================================================================
# EMAIL CONFIGURATION (OUTLOOK)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')

DEFAULT_FROM_EMAIL = f"SYSCLOUD Sistema Integrador <{EMAIL_HOST_USER}>"


# 12. CONFIGURACIÓN FINAL
# ==============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
