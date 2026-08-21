FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

COPY requirements.lock requirements.txt ./
RUN apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --require-hashes -r requirements.txt

RUN groupadd --system app && useradd --system --gid app --home-dir /app app
COPY backend_django /app/backend_django
RUN mkdir -p /app/backend_django/logs /app/backend_django/django_static /app/static \
    && chown -R app:app /app

WORKDIR /app/backend_django
USER app

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
