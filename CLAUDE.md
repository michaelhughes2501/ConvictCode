# CLAUDE.md

Guidance for Claude Code (and humans) when working in this repository.

## Project overview

**ConvictCode** (branded **SecondChance Connect**) is a Flask web application supporting people with prior convictions seeking rehabilitation, community, and a fresh start. Features include user profiles, mutual-like matching, direct messaging, a paginated forum with comments, a curated reentry resources directory, and an Anthropic Claude–powered support chatbot.

## Tech stack

- **Language**: Python 3
- **Framework**: Flask 2.3+
- **ORM**: Flask-SQLAlchemy 3.1+ (SQLite for dev, PostgreSQL/MySQL ready via `DATABASE_URL`)
- **Auth**: Flask-Login (sessions) + `werkzeug.security` password hashes (bcrypt-backed)
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
- **CSRF**: all standard forms use Flask-WTF tokens. Known gap: the `/forum/post/<id>/comment` endpoint accepts JSON without a CSRF token — preserve or fix this deliberately, don't break other forms by accident.
- **Passwords**: always via `generate_password_hash` / `check_password_hash`. Never log password fields.
- **Templates**: extend `base.html`. Bootstrap classes are fine; add custom styles in `static/css/style.css`.
- **Resources data** is currently hardcoded in `app.py` (18 entries). Migrate to a DB table if/when this grows.

## CI/CD

`.github/workflows/` runs CodeQL (Python + JavaScript/TypeScript + Actions), an additional "Bodeql" workflow, and Microsoft Defender for DevOps on push/PR to `main` and on a weekly schedule.

## Known TODOs

- Replace `dev-secret-key-change-in-production` for any non-local environment.
- Add CSRF protection to `/forum/post/<id>/comment`.
- Paginate `/messages`, `/matches`, and search results once the user base grows.
- `templates/profile.htnml` is an empty/typo file — delete or rename if you touch profile templates.
