# Archivo: erp_project/celery.py
import sys

# ¡CLAVE! Solo aplicar el monkey patch si el proceso es un worker de Celery.
# Esto evita que interfiera con 'runserver' y otros comandos de manage.py.
# Verificamos si la palabra 'worker' está en los argumentos del comando.
if 'worker' in sys.argv:
    import eventlet
    eventlet.monkey_patch()

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_project.settings')

app = Celery('erp_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()