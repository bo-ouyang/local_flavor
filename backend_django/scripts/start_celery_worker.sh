#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_DIR}"

export DJANGO_ENV="${DJANGO_ENV:-pro}"

if [ -n "${VIRTUAL_ENV:-}" ]; then
  CELERY_BIN="${VIRTUAL_ENV}/bin/celery"
else
  CELERY_BIN="${PROJECT_DIR}/venv/bin/celery"
fi

if [ ! -x "${CELERY_BIN}" ]; then
  echo "Celery executable not found: ${CELERY_BIN}" >&2
  exit 1
fi

exec "${CELERY_BIN}" -A config worker -l info --concurrency="${CELERY_CONCURRENCY:-2}"
