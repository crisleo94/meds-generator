FROM python:3.12-slim

# Instalar uv directamente desde la imagen oficial
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    DJANGO_DEBUG=False \
    PORT=8000

WORKDIR /app

# Instalar dependencias del sistema mínimas requeridas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de dependencias e instalar con uv sync
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-cache

# Copiar el código del proyecto
COPY . /app/

# Crear directorios para estáticos y subidas efímeras
RUN mkdir -p /app/staticfiles /app/media/uploads

# Recolectar estáticos y ejecutar migraciones usando uv run
RUN uv run python manage.py collectstatic --noinput && \
    uv run python manage.py migrate --noinput

EXPOSE 8000

# Iniciar servidor de producción leyendo la variable PORT (por defecto 8000)
CMD ["sh", "-c", "uv run gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120"]
