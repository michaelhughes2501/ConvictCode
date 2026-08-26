# 08 — Fixed Project Structure

Target layout after Phases A–D of [07-refactor-plan.md](./07-refactor-plan.md) land. Nothing that exists today is deleted — every current file has a home in this tree.

```
ConvictCode/
│
├── README.md                          ← human setup / run / deploy guide
├── CLAUDE.md                          ← AI context (existing, keep tidy)
├── SECURITY.md                        ← existing
├── CHANGELOG.md                       ← added; new
├── LICENSE                            ← optional
│
├── .gitignore                         ← POSIX paths (fixed this pass)
├── .env.example                       ← existing
├── .dockerignore                      ← added
├── Dockerfile                         ← added (Phase D1)
├── Procfile / fly.toml / render.yaml  ← added (Phase D2), pick one
├── pyproject.toml                     ← added: [tool.ruff], [tool.pytest], [tool.mypy]
├── requirements.txt                   ← runtime pins (existing; drop bcrypt/Pillow)
├── requirements-dev.txt               ← added: ruff, pytest, pytest-cov, pip-audit
│
├── convictcode/                       ← app package (renamed from flat layout)
│   ├── __init__.py                    ← create_app() factory
│   ├── extensions.py                  ← db, csrf, login_manager, limiter, talisman, migrate
│   ├── models.py                      ← from database.py (moved)
│   ├── forms.py                       ← extracted from app.py (Phase C1)
│   ├── prompts.py                     ← chat system prompt (Phase C1)
│   ├── resources_data.py              ← RESOURCES list (Phase C1)
│   ├── routes/
│   │   ├── __init__.py                ← register_routes(app) helper
│   │   ├── auth.py                    ← /register, /login, /logout
│   │   ├── profile.py                 ← /profile, /profile/<id>
│   │   ├── social.py                  ← /like, /matches, /search
│   │   ├── messages.py                ← /messages, /messages/<id>
│   │   ├── forum.py                   ← /forum, /forum/new, /forum/post/<id>, comment
│   │   ├── resources.py               ← /resources, /api/resources
│   │   ├── admin.py                   ← /admin/* (Phase A4)
│   │   └── api.py                     ← /api/chat, /api/analytics, /health
│   ├── security/
│   │   ├── boot.py                    ← SECRET_KEY boot-refuse (Phase A3)
│   │   ├── limits.py                  ← Flask-Limiter defaults + overrides (Phase B1)
│   │   └── headers.py                 ← Talisman config + CSP (Phase B2)
│   └── observability/
│       ├── logging.py                 ← JSON logger (Phase C3)
│       └── sentry.py                  ← Sentry init (Phase C2)
│
├── migrations/                        ← Flask-Migrate / Alembic (Phase A5)
│   └── versions/
│       └── 0001_baseline.py
│
├── static/
│   ├── css/style.css                  ← existing
│   └── js/main.js                     ← existing
│
├── templates/                         ← existing 12 templates
│   ├── base.html                      ← add SRI hashes to CDN links (Phase B2)
│   ├── dashboard.html
│   ├── forum.html
│   ├── ...
│   └── admin/                         ← new (Phase A4)
│       ├── analytics.html
│       └── users.html
│
├── instance/                          ← existing; still gitignored; still holds SQLite dev DB
│
├── tests/
│   ├── conftest.py                    ← app factory fixture (Phase A6)
│   ├── test_connectors.py             ← existing (docs-vs-code)
│   ├── test_auth.py                   ← added: register, login, logout, brute-force
│   ├── test_social.py                 ← added: like → mutual → match
│   ├── test_messages.py               ← added: send, list, read-marker
│   ├── test_forum.py                  ← added: post, comment, view increment
│   ├── test_admin.py                  ← added: role gating on /api/analytics
│   ├── test_api_chat.py               ← added: fallback path when ANTHROPIC_API_KEY missing
│   └── test_security.py               ← added: CSRF on POSTs, SECRET_KEY boot-refuse
│
├── docs/
│   ├── connectors.md                  ← existing (test-enforced)
│   ├── runbook.md                     ← added: password reset, ban user, purge post, model bump
│   └── deploy.md                      ← added: managed Postgres, migrations, secret rotation
│
├── .vscode/                           ← existing (extensions/launch/settings)
│
└── .github/
    ├── workflows/
    │   ├── codeql.yml                 ← existing
    │   ├── defender-for-devops.yml    ← existing
    │   ├── tests.yml                  ← added (Phase A7): pytest + ruff + pip-audit
    │   └── docker-build.yml           ← added (Phase D1): verify image builds on PR
    ├── dependabot.yml                 ← added: weekly pip + Actions
    └── instructions/
        └── codacy.instructions.md     ← existing, gitignored
```

## Explicit call-outs

- **`app.py` disappears** as a top-level file. Its contents move to `convictcode/__init__.py` (factory), `convictcode/routes/*.py` (handlers), `convictcode/forms.py`, and `convictcode/resources_data.py`.
- **`database.py` moves to `convictcode/models.py`.** The rename is deliberate — "database.py" was a file-purpose label; "models" is the Django/Flask community convention.
- **The gunicorn command changes** from `gunicorn -w 4 -b 0.0.0.0:5000 app:app` to `gunicorn -w 4 -b 0.0.0.0:5000 "convictcode:create_app()"` (or equivalent). Update `connectors.md` and `SECURITY.md` accordingly.
- **`test_connectors.py` needs a small update** to look for `convictcode/models.py` instead of `database.py`. This is a mechanical PR-2 step.
- **`Bodeql.yml`** (deleted in this pass) does not appear in the target.
- **`.vscode/`** stays as-is; useful for local devs and does not affect deploys.

## Sibling parity

Once this structure lands, the repo will look like:
- **`felonious/backend-flask/`** — the sibling Flask backend in the same org. Same factory pattern, same test layout.
- **`ConvictCode-main/`** — the older / consolidated variant of this same product. Adopting the same shape here makes future consolidation trivial.

Different from:
- **`new-horizon-platform/`** — Supabase-native, no Flask. Uses `supabase/migrations/001_complete_schema.sql` as the DB source of truth. Not something to copy structurally.
- **`ImpactConnect-main/`** — Node/Express/Drizzle. Different stack.
