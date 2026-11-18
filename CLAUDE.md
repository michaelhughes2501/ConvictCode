# CLAUDE.md

Guidance for Claude Code (and humans) when working in this repository.

## Project overview

**ConvictCode** (branded **SecondChance Connect**) is a Flask web application supporting people with prior convictions seeking rehabilitation, community, and a fresh start. Features include user profiles, mutual-like matching, direct messaging, a paginated forum with comments, a curated reentry resources directory, and an Anthropic Claude–powered support chatbot.

## Tech stack

- **Language**: Python 3
- **Framework**: Flask 2.3+
- **ORM**: Flask-SQLAlchemy 3.1+ (SQLite for dev, PostgreSQL/MySQL ready via `DATABASE_URL`)
- **Auth**: Flask-Login (sessions) + `werkzeug.security` password hashes (scrypt by default on modern Werkzeug; `pbkdf2` as the other supported method — `bcrypt` is listed in `requirements.txt` but is not used anywhere in the code)
- **Forms / CSRF**: Flask-WTF + WTForms 3
- **AI**: `anthropic` Python SDK (Claude Haiku for the support chatbot)
- **Server**: Gunicorn (production)
- **Templates**: Jinja2 + Bootstrap CSS, vanilla JS in `static/js/`
- **Imaging**: Pillow

Pinned dependencies live in `requirements.txt`.

## Repo layout

```
ConvictCode/
├── app.py                  # Flask app — all routes, forms, error handlers (≈ 400 lines)
├── database.py             # SQLAlchemy models (User, Message, ForumPost, ForumComment, Like, Match)
├── requirements.txt
├── connectors.md           # Documentation of integrations (DB, auth, env, CSRF, gunicorn, Anthropic)
├── templates/              # Jinja2 templates (base, dashboard, profile, forum, messages, resources, …)
├── static/
│   ├── css/style.css       # ~19 KB stylesheet
│   └── js/main.js          # Chat integration, AJAX, interactivity
├── instance/               # Flask instance folder (SQLite DB lives here)
├── tests/test_connectors.py# unittest suite that validates connectors.md matches the code
├── .github/workflows/      # CodeQL + Defender for DevOps security scans
└── venv/                   # Local virtualenv (gitignored)
```

## Commands

```bash
# One-time setup
python3 -m venv venv
source venv/bin/activate              # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run dev server
python app.py                         # listens on $HOST:$PORT (default 0.0.0.0:5000)

# Run tests
python -m unittest tests.test_connectors
# (or: python -m pytest tests/)

# Production
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Environment

Loaded from `.env` via `python-dotenv`.

| Variable             | Default                                  | Notes                                            |
|----------------------|------------------------------------------|--------------------------------------------------|
| `SECRET_KEY`         | `dev-secret-key-change-in-production`    | **Must** be overridden in production             |
| `DATABASE_URL`       | `sqlite:///felon_dating.db`              | SQLAlchemy URI                                   |
| `HOST`               | `0.0.0.0`                                | Bind address                                     |
| `PORT`               | `5000`                                   | Bind port                                        |
| `FLASK_DEBUG`        | `0`                                      | Set to `1`/`true` for debug mode                 |
| `ANTHROPIC_API_KEY`  | —                                        | Required for `/api/chat`; falls back to canned reply if missing |

Never commit `.env`.

## Database

All models in `database.py` (SQLAlchemy declarative). Tables are auto-created on startup via `db.create_all()` inside an app context.

| Model         | Notes                                                                              |
|---------------|------------------------------------------------------------------------------------|
| `User`        | Profile + reentry fields (crime_type, release_date, rehabilitation_status), dating prefs |
| `Message`     | Direct messages between users (`is_read`, `created_at`)                            |
| `ForumPost`   | Categories: General / Support / Success Stories / Resources; paginated 10/page     |
| `ForumComment`| Cascade-deleted with the post                                                      |
| `Like`        | `UNIQUE(user_id, liked_user_id)` — prevents duplicate likes                        |
| `Match`       | Created when two users have liked each other (mutual flag)                         |

## Key routes

- **Auth**: `GET/POST /register`, `GET/POST /login`, `GET /logout`
- **Profiles**: `GET/POST /profile`, `GET /profile/<user_id>`
- **Matching**: `POST /like/<user_id>` (JSON), `GET /matches`, `GET /search`
- **Messaging**: `GET /messages`, `GET/POST /messages/<user_id>`
- **Forum**: `GET /forum`, `GET/POST /forum/new`, `GET /forum/post/<id>`, `POST /forum/post/<id>/comment`
- **Resources**: `GET /resources`, `GET /api/resources` (JSON)
- **Dashboard**: `GET /dashboard`
- **AI**: `POST /api/chat` (Claude Haiku)
- **Analytics**: `GET /api/analytics` (JSON)

## Conventions

- **Single-file app**: keep route handlers in `app.py` and models in `database.py`. Larger features should still land here unless we agree on splitting into blueprints.
- **`connectors.md` is canonical** integration documentation. If you change DB models, env vars, or the auth/CSRF/gunicorn/Anthropic wiring, **update `connectors.md` and `tests/test_connectors.py` in the same change** — the test suite checks the docs against the code.
- **CSRF**: `CSRFProtect(app)` is initialized globally in `app.py`, so all POST routes (including `/forum/post/<id>/comment`, which accepts form data) are protected by default. If you ever exempt a route with `@csrf.exempt`, document why.
- **Passwords**: always via `generate_password_hash` / `check_password_hash`. Never log password fields.
- **Templates**: extend `base.html`. Bootstrap classes are fine; add custom styles in `static/css/style.css`.
- **Resources data** is currently hardcoded in `app.py` (18 entries). Migrate to a DB table if/when this grows.

## CI/CD

`.github/workflows/` runs CodeQL (Python + JavaScript/TypeScript + Actions) and Microsoft Defender for DevOps on push/PR to `main` and on a weekly schedule.

## Known TODOs

- Replace `dev-secret-key-change-in-production` for any non-local environment.
- Paginate `/messages`, `/matches`, and search results once the user base grows.
- Widen `User.password_hash` from `VARCHAR(128)` to `VARCHAR(255)` / `TEXT` — werkzeug's scrypt hashes exceed 128 chars on non-SQLite backends. See `audit/02-bug-hunt.md` (B3).
- Add `Flask-Migrate` / Alembic before deploying to Postgres; `db.create_all()` cannot alter existing columns.

## Audit reports

See `audit/README.md` for the full engineering audit (bug hunt, security review, refactor plan, target project structure). The Phase-1 pass also deleted `.github/workflows/Bodeql.yml` (a broken/duplicate CodeQL workflow) and fixed the Windows path separator in `.gitignore`.

---

## FeloniousApps build kit (suite-wide defaults)

These are the shared rules from the FeloniousApps build kit. Where they differ from this project's own rules above, this project's rules win.

You are a senior AI + full-stack developer building one of Michael's three-layer web apps. Follow these rules on every change.

### Golden rule
Every site must **run cleanly on localhost with zero errors or bugs, and the code must flow together.** Nothing is "done" until verified.

### Verification loop (run before reporting success)
1. Start the dev server.
2. Tail output; confirm it compiled with no build-breaking errors/warnings.
3. `curl -s -o /dev/null -w "%{http_code}" http://localhost:<port>` → expect `200`.
4. `npm run type-check` (`tsc --noEmit`) → 0 errors.
5. Only then report success. If anything errors, fix and re-verify — never hand back a broken site.

### Stack (default)
- **Frontend:** React 18 + Vite + TypeScript + Tailwind. Functional components + hooks only.
- **Backend/DB:** Supabase (Postgres + Auth + Storage). **RLS ON for every table** with explicit per-user policies. Schema changes go through SQL migrations in `supabase/migrations/` only.
- **AI layer:** Anthropic API. Persistent per-user companion with chat history in Supabase. `claude-sonnet-4-6` for in-app features, `claude-opus-4-8` for heavy reasoning. Send full history each call. Never ship API keys client-side — proxy through an Edge Function / server.
- Routing: React Router. UI: Radix UI (+ shadcn). Icons: lucide-react. Motion: Framer Motion. Tests: Vitest.

### Environment
- Windows + nvm-windows (`nvm use 20`). One dev server per port; kill stale processes first.
- Env vars: read `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` etc. from `.env`. If a var is missing, **fail loudly and name the exact var — never invent values.** Keep `.env.example` complete.
- If npm/installs fail on SSL/TLS, suspect antivirus (AVG) interception.

### Visual standard (enterprise-grade, intriguing)
Dark-first premium UI. Layered surfaces, low-opacity borders, soft shadows, glassmorphism panels (`backdrop-blur`). One bold accent + tasteful gradient on hero/CTAs. Generous whitespace, typographic scale, confident hero headline. Motion: scroll-reveal (fade + rise), button press-scale + hover-lift, card border-glow. Respect `prefers-reduced-motion`. Fully responsive 360→1440px. Accessible: semantic HTML, keyboard nav, focus rings, ARIA, WCAG AA. Loading skeletons, empty states, toasts — never raw spinners on primary content. Drive theme from CSS variables so it swaps in one place.

### Editing discipline
Surgical edits. Keep imports, routes, and naming consistent so the code flows together. Add/update types in `src/types`. Co-locate state; lift to context only when shared.

Reusable patterns for every build: @SKILLS.md
