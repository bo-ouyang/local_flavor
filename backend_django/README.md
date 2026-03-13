# Django Backend (Rewrite)

## Quick Start
1. Install dependencies:
```bash
pip install -r ../requirements-django.txt
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
- `/api/v1`
- Unified response envelope:
```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

## Login
- WeChat login: `POST /api/v1/user/wx-login`
- Phone login: `POST /api/v1/user/phone-login`
  - body example: `{ "phone": "13800000000", "password": "Test@123456" }`

## Admin
- `/admin`
- Manage users/items/comments/flavor tags/messages/system options directly in Django Admin.
- RBAC roles: `super_admin`, `ops_admin`, `content_admin`, `support_admin`, `auditor`.
- Admin visibility and operations are controlled by role(group) permissions.

## Notes
- This rewrite keeps table names compatible with the previous FastAPI schema (`users`, `items`, `comments`, etc.).
- Upload path remains `/static/uploads/...` for frontend compatibility.
- WeChat login endpoint: `POST /api/v1/user/wx-login` with body `{ "code": "wx.login code" }`.
- Init test account for phone login:
```bash
python manage.py init_test_account
```
- Structured logs are written to:
  - `backend_django/logs/app.log`
  - `backend_django/logs/error.log`
