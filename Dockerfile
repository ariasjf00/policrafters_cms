# ============================================================
# Policrafters CMS - Production Dockerfile
# Django / Wagtail
# Python 3.12
# ============================================================


# ------------------------------------------------------------
# Stage 1: Builder
# ------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias necesarias para compilar paquetes Python
# y el driver de PostgreSQL si fuera necesario.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear virtualenv independiente.
RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

# Instalar dependencias primero para aprovechar cache de Docker.
COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt


# ------------------------------------------------------------
# Stage 2: Runtime
# ------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Solo librerías necesarias en runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    zlib1g \
    libwebp7 \
    && rm -rf /var/lib/apt/lists/*

# Copiar virtualenv construido en el stage anterior.
COPY --from=builder /opt/venv /opt/venv

# Crear usuario sin privilegios para Django/Wagtail.
RUN useradd --create-home --shell /bin/bash wagtail

# Copiar código de la aplicación.
COPY . /app

# Crear directorios utilizados por Django/Wagtail.
RUN mkdir -p /app/static /app/media \
    && chown -R wagtail:wagtail /app

USER wagtail

EXPOSE 8000

# El docker-compose.prod.yml se encargará de ejecutar:
#   python manage.py migrate
#   python manage.py collectstatic
#
# Este CMD sirve también como fallback si la imagen
# se ejecuta directamente.
CMD ["gunicorn", "policrafters_cms.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120"]