#!/usr/bin/env bash
set -Eeuo pipefail

RELEASE_TAG=${1:?Usage: bash deploy/release.sh <40-character Git commit SHA>}
PROJECT_NAME="${LOCAL_FLAVOR_PROJECT_NAME:-local_flavor}"
PROJECT_DIR="${LOCAL_FLAVOR_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ENV_FILE="${LOCAL_FLAVOR_ENV_FILE:-$PROJECT_DIR/backend_django/env.prod}"
SECRETS_FILE="${LOCAL_FLAVOR_SECRETS_FILE:-$PROJECT_DIR/backend_django/env.prod.secrets}"
LEGACY_STATIC_DIR="${LOCAL_FLAVOR_LEGACY_STATIC_DIR:-/srv/local_flavor/static}"
BACKUP_DIR="${LOCAL_FLAVOR_BACKUP_DIR:-/srv/local_flavor/backups}"
API_PORT="${LOCAL_FLAVOR_API_PORT:-8001}"
FRONTEND_PORT="${LOCAL_FLAVOR_FRONTEND_PORT:-8002}"
HEALTH_WAIT_SECONDS="${LOCAL_FLAVOR_HEALTH_WAIT_SECONDS:-120}"
IMAGE_OWNER="${LOCAL_FLAVOR_IMAGE_OWNER:-bo-ouyang}"
REGISTRY="${LOCAL_FLAVOR_REGISTRY:-ghcr.io}"
GIT_PROXY="${LOCAL_FLAVOR_GIT_PROXY:-http://127.0.0.1:10809}"

[[ "$RELEASE_TAG" =~ ^[0-9a-f]{40}$ ]] || {
    printf 'Release tag must be a full 40-character lowercase Git commit SHA.\n' >&2
    exit 1
}
[[ "$IMAGE_OWNER" =~ ^[a-z0-9][a-z0-9._-]*$ ]] || {
    printf 'LOCAL_FLAVOR_IMAGE_OWNER must be a lowercase GHCR namespace.\n' >&2
    exit 1
}

BACKEND_IMAGE="$REGISTRY/$IMAGE_OWNER/local-flavor-api:$RELEASE_TAG"
FRONTEND_IMAGE="$REGISTRY/$IMAGE_OWNER/local-flavor-h5:$RELEASE_TAG"

export LOCAL_FLAVOR_ENV_FILE="$ENV_FILE"
export LOCAL_FLAVOR_SECRETS_FILE="$SECRETS_FILE"
export LOCAL_FLAVOR_API_PORT="$API_PORT"
export LOCAL_FLAVOR_FRONTEND_PORT="$FRONTEND_PORT"
export BACKEND_IMAGE
export FRONTEND_IMAGE

compose() {
    docker compose --project-name "$PROJECT_NAME" -f "$PROJECT_DIR/docker-compose.prod.yml" "$@"
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || {
        printf 'Required command not found: %s\n' "$1" >&2
        exit 1
    }
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

previous_backend_image=""
previous_frontend_image=""
release_started=0

previous_image() {
    local service="$1"
    local container
    container="$(compose ps -q "$service" 2>/dev/null || true)"
    [[ -n "$container" ]] || return 0
    docker inspect --format '{{.Config.Image}}' "$container" 2>/dev/null || true
}

rollback() {
    local exit_code=$?
    trap - ERR
    if [[ "$release_started" == "1" && -n "$previous_backend_image" && -n "$previous_frontend_image" ]]; then
        printf 'Release failed; restoring previous application images.\n' >&2
        BACKEND_IMAGE="$previous_backend_image" FRONTEND_IMAGE="$previous_frontend_image" \
            compose up -d --no-build --pull never --remove-orphans || true
    fi
    printf 'Database migrations are forward-only. Restore the pre-release PostgreSQL backup before rolling back incompatible migrations.\n' >&2
    exit "$exit_code"
}
trap rollback ERR

require_command docker
require_command git
require_command curl
require_command find
require_command stat

[[ -f "$ENV_FILE" ]] || { printf 'Production config file not found: %s\n' "$ENV_FILE" >&2; exit 1; }
[[ -f "$SECRETS_FILE" ]] || { printf 'Production secrets file not found: %s\n' "$SECRETS_FILE" >&2; exit 1; }
require_secret_file_permissions

# Source changes update only deployment manifests. The proxy is deliberately
# scoped to this Git transfer; Docker pulls use the daemon's own networking.
git -C "$PROJECT_DIR" diff --quiet
git -C "$PROJECT_DIR" diff --cached --quiet
git -C "$PROJECT_DIR" -c http.proxy="$GIT_PROXY" fetch --depth=1 origin "$RELEASE_TAG"
git -C "$PROJECT_DIR" cat-file -e "$RELEASE_TAG^{commit}"
[[ "$(git -C "$PROJECT_DIR" rev-parse "$RELEASE_TAG^{commit}")" == "$RELEASE_TAG" ]]
git -C "$PROJECT_DIR" checkout --detach "$RELEASE_TAG"

compose config -q
verify_legacy_data
previous_backend_image="$(previous_image api)"
previous_frontend_image="$(previous_image frontend)"

docker pull "$BACKEND_IMAGE"
docker pull "$FRONTEND_IMAGE"
compose pull redis
release_started=1

compose up -d --wait --wait-timeout "$HEALTH_WAIT_SECONDS" redis
report_database_rows
backup_database
compose run --rm --no-deps api python manage.py migrate --noinput
compose run --rm --no-deps api python manage.py collectstatic --noinput
compose up -d --no-build --pull never --remove-orphans --wait --wait-timeout "$HEALTH_WAIT_SECONDS"
report_database_rows
curl --fail --silent --show-error --max-time 10 "http://127.0.0.1:${API_PORT}/" >/dev/null
curl --fail --silent --show-error --max-time 10 "http://127.0.0.1:${FRONTEND_PORT}/health" >/dev/null

printf 'Deployment complete: API %s and H5 frontend %s are running.\n' "$BACKEND_IMAGE" "$FRONTEND_IMAGE"
