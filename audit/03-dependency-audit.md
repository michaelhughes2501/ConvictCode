# 03 — Dependency Audit

## Declared dependencies (`requirements.txt`)

```
Flask>=2.3,<4
Flask-Login>=0.6.3,<1
Flask-SQLAlchemy>=3.1.1,<4
Flask-WTF>=1.2.1,<2
WTForms>=3.1.2,<4
python-dotenv>=1.0.1,<2
bcrypt>=4.1.3,<5
Pillow>=12.2.0,<13
email-validator>=2.2.0,<3
SQLAlchemy>=2.0.30,<3
gunicorn>=22.0.0,<23
anthropic>=0.40.0,<1
```

All pins use range specifiers with an upper cap on the major version — good hygiene, prevents an accidental Flask 4 or SQLAlchemy 3 breaking the app.

## Per-package review

| Package | Pin | Notes |
|---------|-----|-------|
| `Flask` | `>=2.3,<4` | Flask 3.0 is out and API-compatible with the code here. The `render_template`, `redirect`, `url_for`, `flash`, `jsonify`, `request` imports haven't changed. Bump target: `>=3.0,<4`. |
| `Flask-Login` | `>=0.6.3,<1` | Current stable. Fine. |
| `Flask-SQLAlchemy` | `>=3.1.1,<4` | Current stable. Fine. |
| `Flask-WTF` | `>=1.2.1,<2` | Current stable. Fine. |
| `WTForms` | `>=3.1.2,<4` | Current stable. Fine. |
| `python-dotenv` | `>=1.0.1,<2` | Fine. |
| `bcrypt` | `>=4.1.3,<5` | **Unused.** The code uses `werkzeug.security.generate_password_hash`, whose default hasher is scrypt (not bcrypt) on recent Werkzeug. `bcrypt` sits in `requirements.txt` doing nothing. Either wire `werkzeug` to use bcrypt explicitly (`generate_password_hash(pw, method='bcrypt')`) — which does not exist as a Werkzeug method name; the actual method name is `bcrypt` via `passlib`, not Werkzeug — or drop it. Recommendation: drop it. |
| `Pillow` | `>=12.2.0,<13` | Pinned for Python image handling but the app currently does not process or resize uploaded images (`profile_pic` is a filename string only). Unused. Safe to drop unless upload-and-resize is planned. |
| `email-validator` | `>=2.2.0,<3` | Required by WTForms `Email()` validator. Correct. |
| `SQLAlchemy` | `>=2.0.30,<3` | Pinned separately from Flask-SQLAlchemy; harmless (Flask-SQLAlchemy 3.1+ already depends on SA 2). Fine. |
| `gunicorn` | `>=22.0.0,<23` | Current stable. Fine. |
| `anthropic` | `>=0.40.0,<1` | 0.40 is stable, but the SDK has moved forward significantly. The 0.x line has had regular breaking-change minor bumps historically — the `<1` cap is prudent. **Compatibility caveat:** the code uses `client.messages.create` with `model='claude-haiku-4-5-20251001'`. That model ID is real and correct today; if you bump the SDK, verify `response.content[0].text` still works (there was a period where the SDK returned a `TextBlock` object rather than a plain-attr `.text`, but as of 0.40+ this is stable). |

## Unused / suspect

- `bcrypt` — not called anywhere; consider dropping.
- `Pillow` — not called anywhere; consider dropping unless image upload/resize is on the near-term roadmap.

Removing both would trim the wheel-build time and shrink the runtime image (Pillow is one of the larger wheels).

## Known vulnerabilities

`pip-audit` cannot be run here without network, so this section is best-effort against public CVE knowledge:

- No open CVEs known against the pinned Flask / Flask-Login / Flask-WTF / WTForms versions.
- SQLAlchemy 2.0.30+ is clean.
- `gunicorn` 22.x has been advisory-quiet.
- `anthropic` SDK is scoped narrowly; historical advisories have been around log-injection when logs are user-visible, which is not the case here.

Recommendation: enable Dependabot for `pip` in `.github/dependabot.yml`. No such file exists in this repo today.

## Missing dev tooling

- **No `ruff` / `flake8` / `black`** — noted in [01-deep-engineering-audit.md](./01-deep-engineering-audit.md).
- **No `pytest`** — the test suite is written for `unittest` (which is fine), but a `pytest` runner would enable fixture reuse across the tests. `CLAUDE.md` mentions `pytest` as an alternative runner; installing it as an explicit dev dep and adding a `pyproject.toml` `[tool.pytest]` section is a low-friction improvement.
- **No `mypy` / `pyright`** — Flask code without type annotations rarely pays for mypy, but a starter `strict-optional` config would surface at least the `Optional` places where None handling is loose.
- **No `pip-audit` step in CI** — the CodeQL workflow scans Python, but does not scan dependencies. Add a `pip-audit` step (or Dependabot) to close the loop.
- **No `pre-commit` config** — an obvious win for a mixed template + Python + JS repo.

## Missing runtime deps that will be needed shortly

- `Flask-Limiter` — for the rate limiting that today does not exist.
- `Flask-Migrate` (Alembic wrapper) — currently the app auto-`create_all()`s tables on startup, which cannot alter existing columns. First schema change to a deployed instance is a manual migration; formalising this now is a 30-minute job.
- `Flask-Talisman` — for security headers (CSP, X-Frame-Options, etc.). See [04-security-review.md](./04-security-review.md).

## Recommended dependency actions, in order

1. **Add `.github/dependabot.yml`** with a weekly `pip` update job.
2. **Add `ruff` to `requirements-dev.txt`** (create the file) and wire it into CI.
3. **Drop `bcrypt` and `Pillow`** (or wire real usage for either).
4. **Bump `Flask` to `>=3.0,<4`.** Test suite still passes.
5. **Add `Flask-Migrate`** and generate a baseline migration. Every future model change goes through Alembic.
6. **Add `Flask-Limiter`.** Global default (`60/minute`) plus stricter caps on `/login`, `/register`, `/api/chat`.
7. **Add `Flask-Talisman`** with a starter CSP that matches the CDN-loaded Bootstrap + Font Awesome. Note that `base.html` today pulls CSS from `cdn.jsdelivr.net` and `cdnjs.cloudflare.com` — the CSP must allow those origins.
