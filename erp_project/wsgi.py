import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_project.settings')

application = get_wsgi_application()

# AÑADE ESTO: Alias para que Vercel lo reconozca como 'app'
app = application