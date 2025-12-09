#!/bin/sh

# Salir inmediatamente si hay un error
set -e

echo "Aplicando migraciones..."
python manage.py migrate

echo "Recolectando estáticos..."
python manage.py collectstatic --noinput

echo "Iniciando Servidor..."
# Usamos exec para que gunicorn tome el control del proceso (PID 1)
exec python -m gunicorn erp_project.wsgi:application --bind 0.0.0.0:8000
