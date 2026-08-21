# Docker Deployment

This Compose project runs the Django API, Celery worker, and Redis. It does
not create PostgreSQL: the existing host database is used through Docker's
`host-gateway`. Existing uploads stay mounted from `/srv/local_flavor/static`.

## First Server Setup

1. Keep the existing PostgreSQL database and `/srv/local_flavor/static` in
   place. Do not remove either one.
2. Copy `backend_django/env.prod.example` to `backend_django/env.prod`, set
   `DJANGO_ALLOWED_HOSTS` and `LOCAL_FLAVOR_PUBLIC_HOST` to the server public
   IP, and copy the existing DB name and user where they differ from defaults.
3. Copy `backend_django/env.prod.secrets.example` to
   `backend_django/env.prod.secrets`. Put the existing PostgreSQL password and
   Django/WeChat secrets there, then run `chmod 600 backend_django/env.prod.secrets`.
4. Run `bash deploy/deploy.sh`. Before migrations, it verifies the old media
   directory, reports the exact database row count, and writes a custom-format
   PostgreSQL backup under `/srv/local_flavor/backups`.
5. Run `bash deploy/install-nginx.sh` once. Nginx serves the H5 build at
   `http://SERVER_IP:8080/`; the H5 build calls the API on that same HTTP
   origin at `/django/api/v1`.

The deploy script defaults Git, npm, and image-build traffic to
`http://127.0.0.1:10809`. Docker image pulls themselves require the Docker
daemon proxy to be configured when direct registry access is unavailable.

## Updates and Recovery

Run `bash deploy/deploy.sh` from a clean checkout for each update. It builds
the H5 output, refreshes the API image, makes a database backup before every
migration, collects static files, then waits for API (database and Redis) and
Celery worker health checks. The Nginx site keeps serving the H5 directory on
subsequent deployments.

Database migrations are forward-only. To undo an incompatible release, restore
the pre-deploy dump from `/srv/local_flavor/backups` before returning to the
previous revision.
