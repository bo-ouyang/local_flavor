# Project Audit and Bugfix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use systematic debugging and test-driven development task-by-task. This repository started with user-owned uncommitted changes, so verification checkpoints replace automatic commits.

**Goal:** Repair confirmed backend correctness and security defects, restore the frontend type-check workflow, align deployment instructions with the real application, and produce an accurate Chinese project document.

**Architecture:** Preserve the existing Django/DRF and uni-app boundaries. Add focused Django regression tests around public APIs and state transitions, make the smallest production changes that satisfy those tests, and document remaining non-blocking risks instead of broad refactoring.

**Tech Stack:** Python 3.12 and Django 5.2 LTS production target; Python 3.9 and Django 4.2 legacy audit runtime; Django REST Framework, Celery, Channels, Vue 3, uni-app, TypeScript, Pinia.

---

### Task 1: Cache invalidation and item publishing

**Files:**
- Create: `backend_django/core/tests.py`
- Create: `backend_django/items/tests.py`
- Modify: `backend_django/core/cache_utils.py`
- Modify: `backend_django/items/views.py`

- [ ] Write a cache test asserting repeated reads return the current namespace version and a bump is observable.
- [ ] Write an authenticated API test asserting `POST /django/api/v1/items/` creates a pending item and returns HTTP 201.
- [ ] Run both tests and verify failures are `None` cache versions and HTTP 405 respectively.
- [ ] Restore the missing return path in `get_namespace_version()`.
- [ ] Move the item creation handler from `ItemRecommendedView` to `ItemListCreateView` without changing its validation or audit behavior.
- [ ] Run the focused tests and `python manage.py check`.

### Task 2: Business-state and public-data integrity

**Files:**
- Create: `backend_django/exchange/tests.py`
- Create: `backend_django/messaging/tests.py`
- Create: `backend_django/stats/tests.py`
- Create: `backend_django/interactions/tests.py`
- Modify: `backend_django/exchange/views.py`
- Modify: `backend_django/messaging/serializers.py`
- Modify: `backend_django/stats/views.py`
- Modify: `backend_django/interactions/views.py`

- [ ] Write a failing test proving an accepted exchange cannot transition back to pending.
- [ ] Write a failing serializer test proving ordinary clients cannot create `system` messages.
- [ ] Write a failing map-statistics test proving pending, rejected, and invisible items are excluded.
- [ ] Write failing comment tests proving non-public items cannot expose or accept local comments.
- [ ] Implement an explicit exchange transition map while retaining current actor permissions.
- [ ] Remove `system` from the client message serializer choices; internal system notices continue to use the service layer.
- [ ] Filter statistics and local-comment access through visible, approved items, while allowing an owner to read their own pending item comments.
- [ ] Run all new backend tests.

### Task 3: Frontend and dependency consistency

**Files:**
- Modify: `frontend/uni-app/package.json`
- Modify: `frontend/uni-app/package-lock.json`
- Modify: `requirementsdjango.txt`

- [ ] Record the existing `vue-tsc` crash with TypeScript 5.9.3.
- [ ] Pin TypeScript to a version supported by `vue-tsc` 1.8.27 and update the lockfile without changing runtime dependencies.
- [ ] Run `npm run type-check`; fix only real project type errors revealed after the tool starts correctly.
- [ ] Keep the production requirement on supported Django 5.2 LTS and document that the legacy local Python 3.9/Django 4.2 runtime requires migration.
- [ ] Run `npm ls`, `python -m compileall`, and Django system checks.

### Task 4: Deployment and project documentation

**Files:**
- Modify: `backend_django/README.md`
- Modify: `docs/服务器部署文档.md`
- Create: `docs/项目审计与开发文档.md`

- [ ] Correct the dependency filename, Gunicorn command, and `/django/api/v1/` plus `/django/admin/` paths.
- [ ] Document architecture, modules, data flow, authentication, configuration, local startup, Celery, WebSocket fallback, API inventory, testing, deployment, and maintenance guidance.
- [ ] Include an audit ledger separating repaired defects from risks requiring external action, especially the tracked archive containing `.env.local`.
- [ ] Verify every documented command and referenced path against the repository.

### Task 5: Final verification and independent review

**Files:**
- Review all changed files.

- [ ] Run the complete Django test suite.
- [ ] Run Python compilation and `manage.py check`.
- [ ] Run uni-app type checking.
- [ ] Run `git diff --check` and inspect the final diff without overwriting the two pre-existing user changes.
- [ ] Request an independent code review and resolve all critical or important findings.
