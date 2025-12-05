# Usar una imagen base ligera de Python
FROM python:3.10-slim

# Evitar que Python genere archivos .pyc y asegurar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema (necesario para Postgres u otras libs)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del proyecto
COPY . .

# Comando para ejecutar la aplicación usando Gunicorn
# NOTA: Cambia 'erp_project' por el nombre de la carpeta que contiene tu wsgi.py
CMD ["gunicorn", "erp_project.wsgi:application", "--bind", "0.0.0.0:8000"]