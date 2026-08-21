#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_NAME="${LOCAL_FLAVOR_PROJECT_NAME:-local_flavor}"
PROJECT_DIR="${LOCAL_FLAVOR_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
API_PORT="${LOCAL_FLAVOR_API_PORT:-8001}"
FRONTEND_PORT="${LOCAL_FLAVOR_FRONTEND_PORT:-8002}"
LEGACY_STATIC_DIR="${LOCAL_FLAVOR_LEGACY_STATIC_DIR:-/srv/local_flavor/static}"
TEMPLATE="$PROJECT_DIR/deploy/nginx/local_flavor.conf.template"
NGINX_SITE="${LOCAL_FLAVOR_NGINX_SITE:-/etc/nginx/sites-available/local_flavor}"
NGINX_ENABLED="${LOCAL_FLAVOR_NGINX_ENABLED:-/etc/nginx/sites-enabled/local_flavor}"

require_command() {
    command -v "$1" >/dev/null 2>&1 || {
        printf 'Required command not found: %s\n' "$1" >&2
        exit 1
    }
}

require_command docker
require_command nginx
require_command sudo
[[ -f "$TEMPLATE" ]] || { printf 'Template not found: %s\n' "$TEMPLATE" >&2; exit 1; }

volume_path() {
    docker volume inspect --format '{{ .Mountpoint }}' "$1"
}

django_static_dir="$(volume_path "${PROJECT_NAME}_local_flavor_django_static")"
[[ -d "$django_static_dir" && -d "$LEGACY_STATIC_DIR" ]] || {
    printf 'Django static or legacy media is missing. Run deploy/release.sh first.\n' >&2
    exit 1
}

temporary_site="$(mktemp)"
backup_site="$(mktemp)"
had_existing_site=0
cleanup() {
    rm -f "$temporary_site" "$backup_site"
}
trap cleanup EXIT

sed \
    -e "s|__LOCAL_FLAVOR_API_PORT__|$API_PORT|g" \
    -e "s|__LOCAL_FLAVOR_FRONTEND_PORT__|$FRONTEND_PORT|g" \
    -e "s|__LOCAL_FLAVOR_DJANGO_STATIC_DIR__|$django_static_dir|g" \
    -e "s|__LOCAL_FLAVOR_MEDIA_DIR__|$LEGACY_STATIC_DIR|g" \
    "$TEMPLATE" > "$temporary_site"

if sudo test -e "$NGINX_SITE"; then
    sudo cp "$NGINX_SITE" "$backup_site"
    had_existing_site=1
fi

restore_site() {
    if [[ "$had_existing_site" == "1" ]]; then
        sudo cp "$backup_site" "$NGINX_SITE"
    else
        sudo rm -f "$NGINX_SITE"
    fi
}

reload_nginx() {
    if systemctl is-active --quiet nginx; then
        sudo systemctl reload nginx
        return
    fi

    local nginx_master_pid
    nginx_master_pid="$(ps -C nginx -o pid=,args= | awk '/nginx: master process/ {print $1; exit}')"
    [[ -n "$nginx_master_pid" ]] || {
        printf 'Nginx is inactive and no running master process was found.\n' >&2
        exit 1
    }
    sudo kill -HUP "$nginx_master_pid"
}

sudo install -m 0644 "$temporary_site" "$NGINX_SITE"
sudo ln -sfn "$NGINX_SITE" "$NGINX_ENABLED"
if ! sudo nginx -t; then
    restore_site
    sudo nginx -t || true
    exit 1
fi
reload_nginx
printf 'Nginx site installed: http://SERVER_IP:8080/\n'
