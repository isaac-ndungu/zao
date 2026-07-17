FROM python:3.14-slim AS base

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# ---- Stage 2: Dependencies ----
FROM base AS dependencies

# System deps: crypto, PDF (WeasyPrint), pg_dump
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 3: Application ----
FROM dependencies AS application

COPY . .

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Bake static files into the image at build time.
# COLLECTSTATIC=1 skips runtime-only config (DB, secrets) in settings.py;
# the real values are provided at runtime via environment variables.
ENV COLLECTSTATIC=1
ENV DJANGO_SETTINGS_MODULE=zaoapi.settings
RUN python manage.py collectstatic --noinput
ENV COLLECTSTATIC=

EXPOSE 8000

ENTRYPOINT ["sh", "entrypoint.sh"]
