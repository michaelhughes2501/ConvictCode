# 08 — Fixed Project Structure

Target layout after Phases A–D of [07-refactor-plan.md](./07-refactor-plan.md) land. Every current *source* file has a home in this tree; the one deletion is `.github/workflows/Bodeql.yml` (removed in the Phase-1 pass as a broken duplicate of `codeql.yml`), which simply does not appear below.

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
├── templates/                         ← existing 15 templates
│   ├── base.html                      ← add SRI hashes to CDN links (Phase B2)
│   ├── dashboard.html
│   ├── forum.html
│   ├── ...
│   └── admin/                         ← new (Phase A4)
│       ├── analytics.html
│       └── users.html
│   ↑ Flask's default template loader resolves paths relative to the app's root path.
│     Moving code into the `convictcode/` package below moves that root path into the
│     package dir, so this top-level `templates/` stops being discovered automatically.
│     Either move `templates/` and `static/` under `convictcode/`, or pass
│     `Flask(__name__, template_folder='../templates', static_folder='../static')`
│     when the factory runs. See the "Templates/static paths" call-out below.
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
- **`test_connectors.py` needs more than a path rename.** The suite reads `app.py` directly to assert on its app-config section (`CSRFProtect(app)`, `SECRET_KEY` wiring) and its auth section (`generate_password_hash` / `check_password_hash` call sites), plus `database.py` for model shapes. Moving code into `convictcode/__init__.py`, `convictcode/routes/*.py`, `convictcode/forms.py`, and `convictcode/models.py` breaks every one of those `with open('app.py')` reads. The rename must happen in `connectors.md` **and** `tests/test_connectors.py` **and** the model/source paths it checks, all in the same PR as the layout change — otherwise the doc-consistency gate fails on the refactor commit.
- **Templates/static paths.** Moving the app code into `convictcode/` moves `Flask(__name__)`'s root path into the package, and the default Jinja loader will stop finding the top-level `templates/`. Pick one explicitly in the same PR as the factory: either (a) **keep the dirs at the repo root** and construct the Flask app with `template_folder='../templates'` + `static_folder='../static'` (one-line change, no file moves), or (b) **move both dirs under `convictcode/`** so the defaults just work. Option (a) is less disruptive because the templates aren't renamed; option (b) is slightly cleaner for packaging. The target tree above shows option (a).
- **`Bodeql.yml`** (deleted in this pass) does not appear in the target.
- **`.vscode/`** stays as-is; useful for local devs and does not affect deploys.

## Sibling repos in the portfolio

Other Flask apps in the same portfolio exist at `felonious/backend-flask/` and `ConvictCode-main/`. Cross-repo parity claims about their layouts are easier to make true than to prove in this PR, so they're out of scope here — if consolidation is on the roadmap, confirm the factory/test shape of each sibling at that time rather than assuming it.

Different stacks (do not copy structurally):
- **`new-horizon-platform/`** — Supabase-native, no Flask. Uses `supabase/migrations/001_complete_schema.sql` as the DB source of truth.
- **`ImpactConnect-main/`** — Node/Express/Drizzle.
