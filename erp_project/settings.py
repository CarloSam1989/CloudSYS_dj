import os
import environ # Importa la librería
from pathlib import Path
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)
BASE_DIR = Path(__file__).resolve().parent.parent

# --- 2. LEE LAS VARIABLES DE ENTORNO ---
# Lee un archivo .env si existe (útil para desarrollo local)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
# --- FIN DE LA LECTURA ---


# --- 3. AJUSTA TUS VARIABLES CLAVE ---
# Ahora lee las variables desde el entorno
SECRET_KEY = env('SECRET_KEY')

# DEBUG será 'True' solo si hay una variable DEBUG=True en el entorno.
# En Render, no la pondremos, así que será 'False' automáticamente.
DEBUG = env('DEBUG')

# En Render, añade tu dominio aquí, por ejemplo: 'www.misistema.com'
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['.onrender.com'])
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-^+=^zbl!tt(_kx4yg5-rujr&a$y_2y7=4f*kpx1av&6wmp0m=r'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

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
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'erp_project.urls'

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

WSGI_APPLICATION = 'erp_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL'),
        conn_max_age=600
    )
    }
#DATABASES = {
 #   'default': {
  #      'ENGINE': 'django.db.backends.postgresql',
   #     'NAME': 'facturacion_db',
    #    'USER': 'facturacion_user',
     #   'PASSWORD': 'CloudSYS25**',
      #  'HOST': 'localhost', # o la IP de tu servidor de BD
       # 'PORT': '5432',
    #}
#}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
# Al final de settings.py
LOGIN_URL = 'login'
# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
