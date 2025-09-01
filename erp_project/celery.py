# Ubicación: erp_project/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_project.settings')

app = Celery('erp_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()