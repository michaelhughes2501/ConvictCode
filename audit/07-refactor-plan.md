# 07 — Refactor Plan

Ordered, sized, dependency-aware. Each step is a landable PR of its own.

## Ground rules

- `python -m unittest tests.test_connectors` must pass on every PR (docs-vs-code invariant).
- No PR removes a route without a matching template + docs update.
- Every PR that changes `database.py` must be paired with an Alembic migration (once Alembic exists; see A5).
- No PR silently disables CSRF, disables `@login_required`, or narrows a `SECRET_KEY` check.

## Phase A — Correctness + safety (do first)

### A1. Widen `User.password_hash` to `db.String(255)` + migration
- **Priority: highest.** On any non-SQLite backend, this bug hides in the schema and breaks login the day the app migrates off SQLite.
- Effort: 30 min once Alembic is wired (A5). Until then, ship a raw SQL note in `connectors.md` documenting the required `ALTER TABLE`.
- Test: register + login round-trip on SQLite and, if available, a Postgres CI service.

### A2. Migrate `datetime.utcnow()` → `datetime.now(timezone.utc)`
- Effort: 45 min.
- Touches `app.py:131, 366, 367` and `database.py:38, 68, 82, 83, 98, 108, 119`.
- Verification: run under Python 3.12+ and confirm no deprecation warnings.

### A3. Boot-refuse on default `SECRET_KEY` outside dev
- Effort: 15 min.
- Code: at module load, `if os.getenv('SECRET_KEY') is None and os.getenv('FLASK_DEBUG','0') not in ('1','true','yes','on'): raise RuntimeError(...)`.
- Verification: existing tests still pass with `FLASK_DEBUG=1`; boot fails under `FLASK_DEBUG=0` without `SECRET_KEY`.

### A4. Admin-gate `/api/analytics`
- Effort: 30 min.
- Requires an `is_admin` column on `User` (or a `role` field). Combine with A5 (Alembic).
- Verification: add functional test; non-admin gets 403, admin gets 200.

### A5. Add `Flask-Migrate` / Alembic
- Effort: 1 hr.
- Generate a baseline migration matching the current schema. Wire `flask db upgrade` into deploy docs.
- Verification: `flask db current` matches `flask db heads`.

### A6. Add functional tests for the critical paths
- Effort: 3 hrs.
- Minimum coverage: register, login (success + failure), like → mutual → match, send message → read receipt, create forum post → comment, `/api/chat` fallback path when `ANTHROPIC_API_KEY` is missing.
- Wire `pytest` alongside `unittest`; both runners work with the tests we write.

### A7. Add CI job for `pytest`
- Effort: 20 min.
- New `.github/workflows/tests.yml`: matrix of Python 3.11 + 3.12 + 3.13; `pip install -r requirements.txt`, `python -m pytest`.
- Verification: green on the PR.

## Phase B — Hardening

### B1. Add `Flask-Limiter` with sensible defaults
- Effort: 45 min.
- Defaults: `60/minute` per IP. Overrides: `/login` `10/minute`, `/register` `5/hour`, `/api/chat` `30/hour` per user, `/like/<id>` `50/hour` per user.
- Storage: in-memory for dev, Redis for production (document but do not require in a first PR).

### B2. Add `Flask-Talisman` + SRI + strict CSP
- Effort: 1 hr.
- CSP allow-list must include jsdelivr + cdnjs (see [04-security-review.md](./04-security-review.md)).
- Add `integrity=` + `crossorigin="anonymous"` to the two CDN `<link>` tags in `base.html`.
- Verification: hit every route with browser devtools; no CSP violations.

### B3. Cap `add_comment` body length + trim whitespace
- Effort: 15 min. Add a `CommentForm(FlaskForm)` with `TextAreaField(Length(max=2000))` and switch the route to use it.

### B4. Cap `/api/chat` input length + narrow the exception + log failures
- Effort: 30 min. `except anthropic.APIError as e: app.logger.exception(...)`.

### B5. Atomic `views` increment on forum posts
- Effort: 15 min. `.update({'views': ForumPost.views + 1})`.

### B6. Email verification flow
- Effort: 4 hrs. Requires an email-sending dep (`Flask-Mailman` or an outbound provider), a token model, a verify route, and a "resend verification" UX.
- Depends on: A5 (Alembic).

## Phase C — Ergonomics + observability

### C1. Modest source split (see [06-architecture-review.md](./06-architecture-review.md))
- Extract `forms.py`, `resources_data.py`, `prompts.py`.
- Convert `app.py` to an app factory.
- Effort: 2 hrs.
- Verification: `test_connectors.py` still passes (it inspects source text, so the imports must remain resolvable).

### C2. Wire Sentry
- Effort: 30 min. `sentry-sdk[flask]`, DSN from env, one-line init.

### C3. Wire structured logging
- Effort: 45 min. `python-json-logger`, replace the default handler.

### C4. Add `/health` endpoint + gunicorn access-log config
- Effort: 20 min.

## Phase D — Deploy story

### D1. Add `Dockerfile` + `.dockerignore`
- Effort: 30 min.
- Base: `python:3.13-slim`. Copy `requirements.txt`, `pip install`, copy source, run gunicorn.
- Verification: `docker build .` locally, then `docker run -p 5000:5000 ...`.

### D2. Choose a deploy target and commit config
- Fly.io / Render / Railway — pick one, commit `fly.toml` / `render.yaml`.
- Effort: 45 min for a first deploy.

### D3. Managed Postgres + backup docs
- Effort: 2 hrs, mostly documentation.
- Verify: staging env with real Postgres + `flask db upgrade` on deploy.

## Phase E — Product/UX (not blocking prod launch, but referenced in CLAUDE.md TODOs)

### E1. Paginate `/messages`, `/matches`, `/search`
- Effort: 1 hr.

### E2. Move `RESOURCES` to a DB table
- Effort: 2 hrs (schema + migration + admin CRUD screens).

### E3. Second-look on the `Message` cascade-delete behaviour for GDPR
- Effort: 1 hr. Decide whether deleting a user cascades their messages or anonymises them.

## Effort estimate

| Phase | Steps | Effort |
|-------|-------|--------|
| A | 7 | ~7 hrs |
| B | 6 | ~7 hrs |
| C | 4 | ~4 hrs |
| D | 3 | ~4 hrs |
| E | 3 | ~4 hrs |
| **Total** | **23 PRs** | **~26 hrs of engineering time** |

## Explicit non-goals of this refactor

- **No blueprints.** The app is not big enough for blueprints to pay for themselves.
- **No rewrite in a different framework.** Django / FastAPI would each cost weeks and add zero product value.
- **No microservices, no Redis queue, no celery.** Not warranted at current load.
- **No frontend framework.** Server-rendered Jinja2 stays.
- **No Docker Compose stack.** One Dockerfile is enough; add Compose only when Postgres and Redis are both local dev deps.
