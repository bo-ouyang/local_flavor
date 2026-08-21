$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $repoRoot

function Require-File([string] $Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "missing required file: $Path"
    }
}

function Require-Text([string] $Path, [string] $Text) {
    $contents = Get-Content -LiteralPath $Path -Raw
    if (-not $contents.Contains($Text)) {
        throw "missing expected text in ${Path}: $Text"
    }
}

@(
    'Dockerfile',
    'frontend/uni-app/Dockerfile',
    'frontend/uni-app/nginx.conf',
    'docker-compose.prod.yml',
    '.dockerignore',
    'backend_django/env.prod.example',
    'backend_django/env.prod.secrets.example',
    'deploy/release.sh',
    'deploy/nginx/local_flavor.conf.template'
    '.github/workflows/publish-images.yml'
) | ForEach-Object { Require-File $_ }

Require-Text 'Dockerfile' 'CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]'
Require-Text 'frontend/uni-app/Dockerfile' 'npm run build:h5'
Require-Text 'frontend/uni-app/Dockerfile' 'VITE_API_BASE_URL=/django/api/v1'
Require-Text 'frontend/uni-app/nginx.conf' 'location = /health'
Require-Text 'docker-compose.prod.yml' '127.0.0.1:${LOCAL_FLAVOR_API_PORT:-8001}:8000'
Require-Text 'docker-compose.prod.yml' '127.0.0.1:${LOCAL_FLAVOR_FRONTEND_PORT:-8002}:80'
Require-Text 'docker-compose.prod.yml' 'host.docker.internal:host-gateway'
Require-Text 'docker-compose.prod.yml' 'DB_HOST: host.docker.internal'
Require-Text 'docker-compose.prod.yml' '/srv/local_flavor/static:/app/static'
Require-Text 'docker-compose.prod.yml' 'BACKEND_IMAGE:?set BACKEND_IMAGE to an immutable GHCR commit tag'
Require-Text 'docker-compose.prod.yml' 'FRONTEND_IMAGE:?set FRONTEND_IMAGE to an immutable GHCR commit tag'
Require-Text 'docker-compose.prod.yml' "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')"
Require-Text 'docker-compose.prod.yml' 'celery -A config inspect ping'
Require-Text 'docker-compose.prod.yml' 'local_flavor_redis_data'
if ((Get-Content -LiteralPath 'docker-compose.prod.yml' -Raw) -match '(?m)^\s+build:') {
    throw 'Production Compose must pull prebuilt images and must not build on the server'
}
if ((Get-Content -LiteralPath 'docker-compose.prod.yml' -Raw) -match '(?m)^  postgres:') {
    throw 'Compose must reuse the host PostgreSQL database instead of creating a postgres service'
}
Require-Text 'deploy/release.sh' '-c http.proxy="$GIT_PROXY" fetch --depth=1 origin "$RELEASE_TAG"'
Require-Text 'deploy/release.sh' 'checkout --detach "$RELEASE_TAG"'
Require-Text 'deploy/release.sh' 'LOCAL_FLAVOR_PUBLIC_HOST'
Require-Text 'deploy/release.sh' '--header "Host: $PUBLIC_HOST"'
Require-Text 'deploy/release.sh' 'docker pull'
Require-Text 'deploy/release.sh' 'pg_dump'
Require-Text 'deploy/release.sh' 'compose run --rm -T --no-deps api sh -ceu'
Require-Text 'deploy/release.sh' 'verify_legacy_data'
Require-Text 'deploy/release.sh' 'report_database_rows'
Require-Text 'deploy/release.sh' 'migrate --noinput'
Require-Text 'deploy/release.sh' 'collectstatic --noinput'
if ((Get-Content -LiteralPath 'deploy/release.sh' -Raw) -match 'docker compose.*build|npm ci|build:h5|HTTP_PROXY|HTTPS_PROXY') {
    throw 'Release script must use its proxy only for Git and must not build application artifacts on the server'
}
if ((Get-Content -LiteralPath 'deploy/release.sh' -Raw) -match '\$BACKUP_DIR:/backups') {
    throw 'Release script must not give the non-root application container write access to the host backup directory'
}
Require-Text 'deploy/nginx/local_flavor.conf.template' 'listen 8080'
Require-Text 'deploy/nginx/local_flavor.conf.template' 'location /ws/'
Require-Text 'deploy/nginx/local_flavor.conf.template' 'location /django-static/'
Require-Text 'deploy/nginx/local_flavor.conf.template' 'location /static/'
Require-Text 'deploy/nginx/local_flavor.conf.template' 'proxy_pass http://127.0.0.1:__LOCAL_FLAVOR_FRONTEND_PORT__;'
Require-Text 'deploy/install-nginx.sh' 'systemctl is-active --quiet nginx'
Require-Text 'deploy/install-nginx.sh' 'kill -HUP "$nginx_master_pid"'
Require-Text 'backend_django/env.prod.example' 'LOCAL_FLAVOR_PUBLIC_HOST=REPLACE_WITH_SERVER_PUBLIC_IP'
Require-Text 'backend_django/env.prod.secrets.example' 'DJANGO_SECRET_KEY='
Require-Text '.gitignore' 'backend_django/env.prod.secrets'
Require-Text '.github/workflows/publish-images.yml' 'workflow_dispatch:'
Require-Text '.github/workflows/publish-images.yml' 'packages: write'
Require-Text '.github/workflows/publish-images.yml' 'ghcr.io'
Require-Text '.github/workflows/publish-images.yml' 'org.opencontainers.image.revision'
Require-Text '.github/workflows/publish-images.yml' 'github.sha'

Write-Output 'deployment contract passed'
