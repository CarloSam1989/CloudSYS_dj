FROM python:3.12-slim

WORKDIR /app

# Evita problemas con pip
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto completo
COPY . .

# Collect static (solo si usas whitenoise)
RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "erp_project.wsgi:application", "--bind", "0.0.0.0:8000"]
