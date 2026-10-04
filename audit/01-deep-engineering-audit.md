# 01 — Deep Engineering Audit

## Snapshot

| Dimension | State |
|-----------|-------|
| Language | Python 3 (no `python_requires` pinned) |
| Framework | Flask 2.3+ |
| Total Python LOC | ~400 (`app.py`) + ~120 (`database.py`) + ~650 (`tests/`) |
| Templates | 12 Jinja2 templates, all extending `base.html` |
| DB | SQLite dev default, `DATABASE_URL` swappable to Postgres/MySQL |
| Auth | Flask-Login + `werkzeug.security` (PBKDF2/scrypt) |
| CSRF | Flask-WTF, globally initialised, one documented exempt (`/api/chat`) |
| AI | `anthropic` SDK, Claude Haiku for the support chatbot |
| Tests | 5 modules × ~40 tests, all validating that `connectors.md` matches source. **Zero functional route tests.** |
| Lint / formatter | None. |
| CI | CodeQL (Advanced, three-language matrix) + Defender for DevOps + a broken duplicate CodeQL workflow (`Bodeql.yml`, deleted in this pass). |
| Docs | `CLAUDE.md` (AI context), `SECURITY.md`, `connectors.md`. All present, all accurate as of this pass. |

## What works well

- **`connectors.md` + `test_connectors.py`** is a genuinely nice pattern: docs are enforced by tests, so they cannot silently drift from the code. Rare to see in a small Flask app.
- **CSRF is global.** `CSRFProtect(app)` on line 20 protects every POST by default, including `add_comment` (which reads `request.form` directly rather than via a `FlaskForm`). One documented exemption (`/api/chat`) is the correct pattern.
- **Password hashing uses `werkzeug.security`.** No plaintext, salt is per-user, uses timing-safe comparison inside `check_password_hash`.
- **`load_user` is defensive.** Wraps the `db.session.get(User, int(user_id))` in `try/except (TypeError, ValueError)` — a stray non-numeric cookie value can't crash the loader.
- **Jinja2 auto-escapes.** No `|safe` on user-controlled fields in the templates I sampled.
- **Skip-link, `aria-current`, `aria-label` on nav.** Base template shows real accessibility attention.

## Concrete gaps

### G1 — `datetime.utcnow()` is deprecated on Python 3.12+
Every model in `database.py` uses `default=datetime.utcnow`, and `app.py` uses `datetime.utcnow()` in `login` (line 131) and `analytics` (line 366). On Python 3.12+, calling `datetime.utcnow()` emits a `DeprecationWarning`; on Python 3.15+ it's slated for removal. The compat migration is `datetime.now(timezone.utc)` (or `datetime.UTC` on 3.11+). The `current_year` context processor at line 397 was already migrated; the rest was left.

### G2 — `User.password_hash` is `VARCHAR(128)` — too narrow for scrypt
`werkzeug.security.generate_password_hash` defaults to scrypt in modern versions, and scrypt hashes can exceed 128 characters (typically ~135–170). On SQLite the column length is advisory, but on **PostgreSQL and MySQL** a hash longer than 128 chars will be **silently truncated on insert and refuse to verify on login**. This is a config-only environment away from a production login outage. Recommend `db.String(255)` or `db.Text`.

### G3 — No functional tests
`tests/test_connectors.py` verifies docs against code. It does not exercise a single route. There is no test for register/login, no test for the mutual-like → match flow, no test for CSRF, no test for the chatbot's fallback path. First feature-affecting bug that lands will not be caught in CI.

### G4 — `lint` script is missing entirely
There is no `ruff`, no `flake8`, no `black`, no `mypy`. The `SECURITY.md` claim of "we run static analysis" is CodeQL + Defender only — those are security scanners, not lint. Recommend `ruff` + `ruff format` as the minimum.

### G5 — `analytics` route is `@login_required` but not admin-gated
Any authenticated user can `GET /api/analytics` and see total user counts, message counts, forum post counts, and rolling weekly deltas. This is aggregate data — not PII — but it's a leak that reveals platform size and growth to competitors and to anyone who registers.

### G6 — `view_post` is anonymous and increments views on every hit
```python
@app.route('/forum/post/<int:post_id>')
def view_post(post_id):
    post = ForumPost.query.get_or_404(post_id)
    post.views += 1
    db.session.commit()
```
No auth gate, no rate-limit, no idempotency, no distinct-visitor deduplication. `curl` in a loop bumps any post to arbitrary view counts. Also a race under concurrent access (read-modify-write without `UPDATE ... SET views = views + 1` semantics).

### G7 — Anthropic client is created per request
In `chat()`, `anthropic.Anthropic(api_key=...)` runs on every call. The client keeps an HTTP connection pool internally — recreating it per request wastes handshakes and leaks descriptors under load. Should be module-level.

### G8 — `SECRET_KEY` has a weak default and no production check
`app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')` starts fine even in production. The name-shaming default doesn't prevent gunicorn from booting with it. A cheap defence: refuse to boot if `SECRET_KEY == the default` and `FLASK_DEBUG` is off.

### G9 — Rate limiting: none, anywhere
- No per-user rate limit on `/api/chat` — Anthropic costs run linear with user requests.
- No per-IP rate limit on `/login` — brute-force possible.
- No per-user rate limit on `/like`, `/messages/<id>` — spam possible.
- No captcha on `/register`.

`Flask-Limiter` is the standard drop-in.

### G10 — `pysa.yml` and `Bodeql.yml` had been sitting broken
`Bodeql.yml` was deleted this pass. `pysa.yml` is not present in this repo (it's in NewHorizonV2 / new-horizon-platform); noted here only because the sibling repos should benefit from the same clean-up.

## Code smell inventory (rank-ordered)

| Rank | Smell | Where |
|------|-------|-------|
| 1 | `app.py` is a 400-line "everything file" | `app.py` |
| 2 | Static `RESOURCES` list mixed with route handlers | `app.py:76–95` |
| 3 | Long inline `Match.query.filter(...)` predicates | `app.py:142, 170, 282` |
| 4 | `IntegerField('Age', validators=[NumberRange(min=18, max=120)])` but no DB constraint | `app.py:48` |
| 5 | `first_name` + `last_name` joined without null-guarding both | `database.py:55` (harmless — falsy short-circuits) |
| 6 | Manual `read/update/commit` on messages instead of `.update(synchronize_session=False)` | `app.py:223` |
| 7 | `search` route iterates `.contains()` — leaks LIKE metacharacters | `app.py:302–311` |

## Verdict

The scaffold is coherent — CSRF wired correctly, docs-as-tests, real accessibility care in the templates. What's missing is the boring, load-bearing stuff: real tests, a linter, a rate limiter, an admin gate on analytics, a longer `password_hash` column, and a Python 3.12+ compatibility pass on `datetime.utcnow`. None of these are large jobs. The refactor plan orders them.
