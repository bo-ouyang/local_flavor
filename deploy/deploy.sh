#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_NAME="${LOCAL_FLAVOR_PROJECT_NAME:-local_flavor}"
PROJECT_DIR="${LOCAL_FLAVOR_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ENV_FILE="${LOCAL_FLAVOR_ENV_FILE:-$PROJECT_DIR/backend_django/env.prod}"
SECRETS_FILE="${LOCAL_FLAVOR_SECRETS_FILE:-$PROJECT_DIR/backend_django/env.prod.secrets}"
LEGACY_STATIC_DIR="${LOCAL_FLAVOR_LEGACY_STATIC_DIR:-/srv/local_flavor/static}"
BACKUP_DIR="${LOCAL_FLAVOR_BACKUP_DIR:-/srv/local_flavor/backups}"
API_PORT="${LOCAL_FLAVOR_API_PORT:-8001}"
HEALTH_WAIT_SECONDS="${LOCAL_FLAVOR_HEALTH_WAIT_SECONDS:-120}"

export LOCAL_FLAVOR_ENV_FILE="$ENV_FILE"
export LOCAL_FLAVOR_SECRETS_FILE="$SECRETS_FILE"
export LOCAL_FLAVOR_LEGACY_STATIC_DIR="$LEGACY_STATIC_DIR"
export LOCAL_FLAVOR_API_PORT="$API_PORT"
export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:10809}"
export HTTPS_PROXY="${HTTPS_PROXY:-$HTTP_PROXY}"
export NO_PROXY="${NO_PROXY:-127.0.0.1,localhost,host.docker.internal,redis}"
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export no_proxy="$NO_PROXY"

compose() {
    docker compose --project-name "$PROJECT_NAME" -f "$PROJECT_DIR/docker-compose.prod.yml" "$@"
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || {
        printf 'Required command not found: %s\n' "$1" >&2
        exit 1
    }
}

read_env_value() {
    local key="$1"
    local file="$2"
    awk -v key="$key" 'index($0, key "=") == 1 { print substr($0, length(key) + 2); exit }' "$file"
}

require_secret_file_permissions() {
    local mode
    mode="$(stat -c '%a' "$SECRETS_FILE")"
    if (( (8#$mode & 077) != 0 )); then
        printf 'Secrets file must not be readable by group or others: %s\n' "$SECRETS_FILE" >&2
        exit 1
    fi
}

verify_legacy_data() {
    [[ -d "$LEGACY_STATIC_DIR" ]] || {
        printf 'Legacy static directory not found: %s\n' "$LEGACY_STATIC_DIR" >&2
        exit 1
    }
    local file_count
    file_count="$(find "$LEGACY_STATIC_DIR" -type f -print | wc -l | tr -d '[:space:]')"
    printf 'Legacy media verified: %s files in %s.\n' "$file_count" "$LEGACY_STATIC_DIR"
}

report_database_rows() {
    compose run --rm --no-deps api python -c '
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.db import connection

tables = connection.introspection.table_names()
with connection.cursor() as cursor:
    total = 0
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {connection.ops.quote_name(table)}")
        total += cursor.fetchone()[0]
print(f"Database verified: {total} rows across {len(tables)} tables.")
'
}

backup_database() {
    local timestamp backup_file
    timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
    backup_file="local_flavor-${timestamp}.dump"
    install -d -m 0700 "$BACKUP_DIR"
    compose run --rm --no-deps -v "$BACKUP_DIR:/backups" api sh -ceu '
        export PGPASSWORD="$DB_PASSWORD"
        pg_dump --format=custom --no-owner --no-privileges \
            --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --dbname="$DB_NAME" \
            --file="/backups/'"$backup_file"'"
    '
    printf 'PostgreSQL backup created: %s/%s\n' "$BACKUP_DIR" "$backup_file"
}

build_h5() {
    local public_host="$1"
    pushd "$PROJECT_DIR/frontend/uni-app" >/dev/null
    VITE_API_BASE_URL="http://${public_host}:8080/django/api/v1" \
        VITE_CHAT_ENABLE_WS=1 \
        npm ci
    VITE_API_BASE_URL="http://${public_host}:8080/django/api/v1" \
        VITE_CHAT_ENABLE_WS=1 \
        npm run build:h5
    popd >/dev/null
}

previous_revision=""
release_switched=0

rollback() {
    local exit_code=$?
    trap - ERR
    if [[ "$release_switched" == "1" && -n "$previous_revision" ]]; then
        printf 'Deployment failed; restoring source revision %s.\n' "$previous_revision" >&2
        git -C "$PROJECT_DIR" reset --hard "$previous_revision" || true
        build_h5 "$PUBLIC_HOST" || true
        compose build api || true
        compose up -d --no-build --remove-orphans || true
    fi
    printf 'Database migrations are forward-only. Restore the pre-deploy PostgreSQL backup before rolling back incompatible migrations.\n' >&2
    exit "$exit_code"
}
trap rollback ERR

require_command docker
require_command git
require_command curl
require_command find
require_command npm
require_command stat

[[ -f "$ENV_FILE" ]] || { printf 'Production config file not found: %s\n' "$ENV_FILE" >&2; exit 1; }
[[ -f "$SECRETS_FILE" ]] || { printf 'Production secrets file not found: %s\n' "$SECRETS_FILE" >&2; exit 1; }
require_secret_file_permissions

PUBLIC_HOST="$(read_env_value LOCAL_FLAVOR_PUBLIC_HOST "$ENV_FILE")"
[[ -n "$PUBLIC_HOST" && "$PUBLIC_HOST" != REPLACE_WITH_* ]] || {
    printf 'LOCAL_FLAVOR_PUBLIC_HOST must be set to the server public IP in %s\n' "$ENV_FILE" >&2
    exit 1
}

git -C "$PROJECT_DIR" diff --quiet
git -C "$PROJECT_DIR" diff --cached --quiet
previous_revision="$(git -C "$PROJECT_DIR" rev-parse HEAD)"

git -C "$PROJECT_DIR" pull --ff-only
release_switched=1

compose config -q
verify_legacy_data
build_h5 "$PUBLIC_HOST"
compose build api
compose up -d --wait --wait-timeout "$HEALTH_WAIT_SECONDS" redis
report_database_rows
backup_database
compose run --rm --no-deps api python manage.py migrate --noinput
compose run --rm --no-deps api python manage.py collectstatic --noinput
compose up -d --no-build --remove-orphans --wait --wait-timeout "$HEALTH_WAIT_SECONDS"
report_database_rows
curl --fail --silent --show-error --max-time 10 "http://127.0.0.1:${API_PORT}/" >/dev/null

printf 'Deployment complete: http://%s:8080/ is served by Nginx and API health checks passed.\n' "$PUBLIC_HOST"
