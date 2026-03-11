FROM python:3.11-slim-bookworm

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y hacer la caché de pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Exponer el puerto de django
EXPOSE 8000

# Comando para correr, puedes adaptarlo usando gunicorn en prod
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
