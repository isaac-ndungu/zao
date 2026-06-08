# ---- Stage 1: Base ----
FROM python:3.14-slim AS base

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# ---- Stage 2: Dependencies ----
FROM base AS dependencies

# System packages: build-essential + libffi-dev for cryptography,
# libpango/libcairo for WeasyPrint PDF generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 3: Application ----
FROM dependencies AS application

COPY . .

EXPOSE 8000

CMD python manage.py collectstatic --noinput --clear && \
    gunicorn zaoapi.wsgi:application --bind 0.0.0.0:8000 --workers 4
