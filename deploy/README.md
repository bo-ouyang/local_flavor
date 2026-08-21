# GHCR Image Deployment

The server never builds application images. GitHub Actions publishes an API
image and an H5 image to GHCR for each `main` commit, then the server pulls the
exact 40-character commit tag. Compose runs Django, Celery, H5 Nginx, and
Redis. PostgreSQL remains on the host through Docker's `host-gateway`, and
uploads remain mounted from `/srv/local_flavor/static`.

## Package Visibility

The repository being public does not automatically make a newly created GHCR
package public. After the first successful `Publish GHCR Images` workflow,
open each package's GitHub **Package settings** and set its visibility to
**Public**:

- `ghcr.io/bo-ouyang/local-flavor-api`
- `ghcr.io/bo-ouyang/local-flavor-h5`

After both packages are public, the server runs `docker pull` without a GitHub
login or PAT. Until then, a registry login with a package-read token is needed.

## First Server Setup

1. Keep the existing PostgreSQL database and `/srv/local_flavor/static` in
   place. Do not remove either one.
2. Copy `backend_django/env.prod.example` to `backend_django/env.prod`, set
   `DJANGO_ALLOWED_HOSTS` and `LOCAL_FLAVOR_PUBLIC_HOST` to the server public
   IP, and copy the existing DB name and user where they differ from defaults.
3. Copy `backend_django/env.prod.secrets.example` to
   `backend_django/env.prod.secrets`. Put the existing PostgreSQL password and
   Django/WeChat secrets there, then run `chmod 600 backend_django/env.prod.secrets`.
4. Publish the commit on `main` with the `Publish GHCR Images` workflow. Copy
   its full commit SHA from GitHub.
5. Run `bash deploy/release.sh <40-character-commit-sha>`. Before migrations,
   it verifies old media, reports database rows, and writes a custom-format
   PostgreSQL backup under `/srv/local_flavor/backups`.
6. Run `bash deploy/install-nginx.sh` once. Host Nginx proxies the H5 image at
   `http://SERVER_IP:8080/` and proxies the API on that same origin.

`LOCAL_FLAVOR_GIT_PROXY` defaults to `http://127.0.0.1:10809` and is passed
only to `git pull`. Docker does not receive `HTTP_PROXY` or build arguments;
when direct registry access is blocked, configure the Docker daemon proxy
separately so `docker pull` can reach GHCR.

## Updates and Recovery

For each update, publish the `main` commit and run:

```bash
bash deploy/release.sh <40-character-commit-sha>
```

The script checks out the same exact commit, pulls immutable API and H5 images,
backs up PostgreSQL before every migration, collects static files, and waits
for API, Celery, Redis, and H5 health checks. On an application startup failure
it restores the prior images. Database migrations are forward-only, so restore
the pre-release dump before rolling back an incompatible schema migration.
