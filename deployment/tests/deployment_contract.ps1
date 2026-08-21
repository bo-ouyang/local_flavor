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
    'docker-compose.prod.yml',
    '.dockerignore',
    'backend_django/env.prod.example',
    'backend_django/env.prod.secrets.example',
    'deploy/deploy.sh',
    'deploy/nginx/local_flavor.conf.template'
) | ForEach-Object { Require-File $_ }

Require-Text 'Dockerfile' 'CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]'
Require-Text 'docker-compose.prod.yml' '127.0.0.1:${LOCAL_FLAVOR_API_PORT:-8001}:8000'
Require-Text 'docker-compose.prod.yml' 'host.docker.internal:host-gateway'
Require-Text 'docker-compose.prod.yml' 'DB_HOST: host.docker.internal'
Require-Text 'docker-compose.prod.yml' '/srv/local_flavor/static:/app/static'
Require-Text 'docker-compose.prod.yml' "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')"
Require-Text 'docker-compose.prod.yml' 'celery -A config inspect ping'
Require-Text 'docker-compose.prod.yml' 'local_flavor_redis_data'
if ((Get-Content -LiteralPath 'docker-compose.prod.yml' -Raw) -match '(?m)^  postgres:') {
    throw 'Compose must reuse the host PostgreSQL database instead of creating a postgres service'
}
Require-Text 'deploy/deploy.sh' 'HTTP_PROXY'
Require-Text 'deploy/deploy.sh' 'docker compose'
Require-Text 'deploy/deploy.sh' 'pg_dump'
Require-Text 'deploy/deploy.sh' 'verify_legacy_data'
Require-Text 'deploy/deploy.sh' 'report_database_rows'
Require-Text 'deploy/deploy.sh' 'migrate --noinput'
Require-Text 'deploy/deploy.sh' 'collectstatic --noinput'
Require-Text 'deploy/deploy.sh' 'npm ci'
Require-Text 'deploy/deploy.sh' 'build:h5'
Require-Text 'deploy/deploy.sh' 'build_h5 "$PUBLIC_HOST" || true'
Require-Text 'deploy/nginx/local_flavor.conf.template' 'listen 8080'
Require-Text 'deploy/nginx/local_flavor.conf.template' 'location /ws/'
Require-Text 'deploy/nginx/local_flavor.conf.template' 'location /django-static/'
Require-Text 'deploy/nginx/local_flavor.conf.template' 'location /static/'
Require-Text 'deploy/nginx/local_flavor.conf.template' 'root __LOCAL_FLAVOR_H5_DIR__;'
Require-Text 'deploy/nginx/local_flavor.conf.template' 'try_files $uri $uri/ /index.html;'
Require-Text 'backend_django/env.prod.example' 'LOCAL_FLAVOR_PUBLIC_HOST=REPLACE_WITH_SERVER_PUBLIC_IP'
Require-Text 'backend_django/env.prod.secrets.example' 'DJANGO_SECRET_KEY='
Require-Text '.gitignore' 'backend_django/env.prod.secrets'

Write-Output 'deployment contract passed'
