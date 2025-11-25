import os
from pathlib import Path
import environ
import dj_database_url

# 1. CONFIGURACIÓN INICIAL Y DE ENTORNO
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

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
<<<<<<< HEAD

# En Render, añade tu dominio aquí, por ejemplo: 'www.misistema.com'
#ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['.onrender.com'])
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/



# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []
=======
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['.onrender.com'])
>>>>>>> a8c9b190f90a6a728a980e54d39587ef531f4f5e


# 3. APLICACIONES Y MIDDLEWARE
# ==============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
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
# Asegúrate de que 'CloudSYS' es el nombre correcto de tu carpeta de proyecto
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


<<<<<<< HEAD
#DATABASES = {
#    'default': dj_database_url.config(
#        default=env('DATABASE_URL'),
#        conn_max_age=600
#    )
#    }
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'facturacion_db',
        'USER': 'facturacion_user',
        'PASSWORD': 'CloudSYS25**',
        'HOST': 'localhost', # o la IP de tu servidor de BD
        'PORT': '5432',
    }
=======
# 6. BASE DE DATOS
# ==============================================================================
# dj-database-url leerá la variable DATABASE_URL de Render y la configurará por ti.
DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL'),
        conn_max_age=600
    )
>>>>>>> a8c9b190f90a6a728a980e54d39587ef531f4f5e
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
STATIC_URL = 'static/'
# Para desarrollo local
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
# Para producción (Render necesita esta línea)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Para que WhiteNoise sirva los archivos de forma eficiente
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# 10. CONFIGURACIÓN DE CELERY
# ==============================================================================
# Lee la URL de Redis desde las variables de entorno de Render
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')


# 11. CONFIGURACIÓN DE CORREO (EJEMPLO)
# ==============================================================================
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = env('EMAIL_HOST')
# EMAIL_PORT = env.int('EMAIL_PORT')
# EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS')
# EMAIL_HOST_USER = env('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
# DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')


# 12. CONFIGURACIÓN FINAL
# ==============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
