# Django Backend (Rewrite)

## Quick Start

The backend runtime is Python 3.12 and Django 5.2 LTS. The repository's
`.python-version` pins the Python minor release used by local tools and CI.

1. Install dependencies:
```bash
python -m pip install --require-hashes -r ../requirements.lock
```
2. Select environment profile (read from `env.dev` / `env.pro`):
```bash
# dev (default)
$env:DJANGO_ENV='dev'

# production
$env:DJANGO_ENV='pro'
```
`settings.py` will auto-load `backend_django/env.dev` or `backend_django/env.pro`.
3. Run migrations:
```bash
python manage.py makemigrations users items exchange interactions messaging system_config
python manage.py migrate
```
4. Create admin account:
```bash
python manage.py createsuperuser
```
5. Initialize RBAC roles:
```bash
python manage.py init_rbac
python manage.py assign_admin_role --username your_admin --role ops_admin
```
6. Start server:
```bash
python manage.py runserver 0.0.0.0:8001
```

## API Prefix
- `/django/api/v1`
- Unified response envelope:
```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

## Login
- WeChat login: `POST /django/api/v1/user/wx-login`
- Phone login: `POST /django/api/v1/user/phone-login`
  - body example: `{ "phone": "13800000000", "password": "Test@123456" }`

## Admin
- `/django/admin/`
- Manage users/items/comments/flavor tags/messages/system options directly in Django Admin.
- RBAC roles: `super_admin`, `ops_admin`, `content_admin`, `support_admin`, `auditor`.
- Admin visibility and operations are controlled by role(group) permissions.

## Notes
- This rewrite keeps table names compatible with the previous FastAPI schema (`users`, `items`, `comments`, etc.).
- Upload path remains `/static/uploads/...` for frontend compatibility.
- WeChat login endpoint: `POST /django/api/v1/user/wx-login` with body `{ "code": "wx.login code" }`.
- Init test account for phone login:
```bash
python manage.py init_test_account
```
- Structured logs are written to:
  - `backend_django/logs/app.log`
  - `backend_django/logs/error.log`

## Checks and Tests

```bash
python manage.py check
python manage.py test
```

## Dependency policy

- `../requirements.in` contains 10 reviewed direct Django runtime dependencies. `celery[redis]` activates Celery's supported Redis transport, while the explicit `redis>=4.6,!=5.0.2,<6.5` range records the application's direct Django RedisCache dependency and the intersection of Channels Redis and Kombu constraints.
- `../requirements.lock` pins 49 transitive packages and their distribution hashes for CI and production; the current lock uses Celery 5.6.3, Kombu 5.6.2, and redis-py 6.4.0.
- `../requirements.txt` is the standard compatibility entry point and includes `requirements.lock`; it no longer contains the retired FastAPI stack.
- Do not edit `requirements.lock` manually. Regenerate it from the repository root with uv 0.9.5:

```bash
uv pip compile requirements.in --python-version 3.12 --universal --generate-hashes --output-file requirements.lock
```

After regeneration, install the lock in a clean Python 3.12 environment and run
`python -m pip check` plus the checks above.

The transport checker can validate metadata and non-eager Celery configuration on a
machine without Redis. Its test supplies isolated local URLs and does not connect:

```bash
python -m unittest discover -s .github/scripts -p 'test_check_celery_redis_transport.py' -v
```

CI additionally runs `check_celery_redis_transport.py --ping` against its disposable
Redis 7 service. It only loads the broker/result transports and sends `PING`; it does
not publish tasks or write keys.

References: [Celery 5.6 Redis documentation](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html)
and [Django 5.2 Redis cache documentation](https://docs.djangoproject.com/en/5.2/topics/cache/#redis).
