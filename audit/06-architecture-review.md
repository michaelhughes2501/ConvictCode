# 06 — Architecture Review

## Current architecture

```
Browser
   │
   ▼
gunicorn (production) / flask run (dev)
   │
   ▼
Flask app (single module, app.py)
   ├── CSRFProtect(app)
   ├── LoginManager(app)
   ├── SQLAlchemy(app) → SQLite (instance/felon_dating.db)
   │
   ├── ~15 route handlers (auth, profile, matching, messaging, forum, resources, analytics, chat)
   ├── 5 WTForms classes inline
   └── 1 static RESOURCES list (18 hardcoded entries)
```

Everything lives in `app.py` (~400 lines) and `database.py` (~120 lines). The convention documented in `CLAUDE.md` is: "**Single-file app**: keep route handlers in `app.py` and models in `database.py`." That is a legitimate design choice for a small Flask app.

## Where the single-file convention starts to strain

At ~400 lines, `app.py` still fits on a small monitor. The strain shows in:

1. **Forms are inline with routes.** `RegistrationForm`, `LoginForm`, `ProfileForm`, `ForumPostForm`, `MessageForm` all live in `app.py`. A future 3–5 additional forms (post-edit, comment-edit, admin-user, admin-post, password-reset) push this past 500 lines.
2. **The `RESOURCES` list is hardcoded in the app module.** 18 entries × ~4 fields each = ~80 lines that have nothing to do with routing. `CLAUDE.md` already flags this as a TODO.
3. **The chat prompt is inline.** ~10 lines of system prompt buried in `app.py:344–351`. If it ever needs A/B testing, or per-user customisation, it will fight the route function it lives inside.
4. **Two big query predicates repeat.** `Match.query.filter(((Match.user1_id == cur) | (Match.user2_id == cur)) & (Match.is_mutual == True))` appears on lines 142 and 282. Any change to matching logic has to happen in both places.

## Recommended layering — modest split, not a rewrite

The `CLAUDE.md` convention is to keep this app single-file. That is defensible. A **modest** split into 4 modules is enough to remove the pain points without breaking the convention or requiring blueprints:

```
convictcode/
├── app.py               ← Flask app factory + registrations only (30–50 LOC)
├── database.py          ← models only (as today)
├── forms.py             ← the five WTForms classes
├── resources_data.py    ← the RESOURCES list + helpers
├── routes.py            ← all route handlers (or split further later)
└── prompts.py           ← chat system prompt(s)
```

`app.py` becomes:

```python
def create_app():
    app = Flask(__name__)
    app.config.from_prefixed_env('FLASK')  # or explicit load
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    from .routes import register_routes
    register_routes(app)
    return app
```

Benefits, in order:
- **Testable factory.** Functional tests instantiate `create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})` per test.
- **Focused files.** Each file changes for one reason.
- **Zero blueprint overhead.** Blueprints are a fine next step (if / when the app doubles in size); they are not required right now.

## Data layer

- **Models are correct.** `UNIQUE(user_id, liked_user_id)` on `Like` prevents duplicate likes. Cascade on `ForumPost` → `ForumComment`. FK constraints on all relationships.
- **Missing indexes.** For a real user base:
  - `Message.recipient_id, is_read` — every dashboard load hits this.
  - `Message.sender_id, recipient_id, created_at` — every conversation load.
  - `ForumPost.created_at DESC` — pagination.
  - `Like.liked_user_id` — every dashboard.
- **`Match.is_mutual` should probably not exist.** Every row in `matches` is created only when a mutual like happens (see `like_user`). The column is always True. If a "one-sided match" case is expected, keep it; if not, drop it.
- **`ForumPost.updated_at` uses `default + onupdate=datetime.utcnow`** — correct pattern; will need the same 3.12+ timezone-aware migration as other timestamps.

## Auth layer

- **Session-based** (Flask-Login), single-tab-safe, no JWT complexity. Correct choice for this app class.
- **`AnonymousUserMixin` behaviour** is default; `current_user.is_authenticated` short-circuits every guarded operation. Correct.

## Presentation layer

- **Server-rendered Jinja2** + Bootstrap 5.3 + Font Awesome. Correct for the app's scale.
- **CSS-in-CDN** (`cdn.jsdelivr.net`, `cdnjs.cloudflare.com`) — see [04-security-review.md](./04-security-review.md) about SRI and CSP.
- **JS is vanilla** (`static/js/main.js` — dark mode toggle, tooltips, textarea counters, password toggle). No framework, no build step. Correct.
- **Theme is a client-side preference** stored in `localStorage`. Correct pattern (flash-of-unstyled-content guard is inlined in `<head>`).

## API layer

- **`/api/chat`, `/api/analytics`, `/api/resources`** — three JSON endpoints. Naming is consistent. Each returns `application/json`.
- **No OpenAPI schema.** A tiny app can live without one; the moment a mobile client (e.g. `NewHorizon_Android`) starts consuming these endpoints, publish a schema.
- **No versioning prefix (`/api/v1/`).** Fine for now; consider before ever making a breaking change.

## Cross-cutting concerns

- **Config** — read via `os.getenv` inline. Fine at this scale; move to a `Config` class (`class DevConfig`, `class ProdConfig`) if / when the config surface exceeds ~6 knobs.
- **Logging** — none custom.
- **Cache** — none. Not needed for the current load; consider `Flask-Caching` around the static `RESOURCES` list once it grows.
- **Background jobs** — none. Not needed. If email-verification or scheduled digests ever land, add `rq` or `celery` — not before.

## Boundaries diagram (target)

```
gunicorn
   │
   ▼
create_app()  ── config, extensions, blueprints
   ├── auth blueprint             (register, login, logout, password reset)
   ├── social blueprint           (profile, search, view_profile, like, matches)
   ├── messages blueprint         (messages, conversation)
   ├── forum blueprint            (forum, new_post, view_post, comment)
   ├── api blueprint              (/api/chat, /api/resources, /api/analytics)
   └── admin blueprint            (once admin role exists)
```

Blueprint splits are recommended **once the app exceeds ~800 LOC across `routes.py`**, not before. Current size does not warrant it.

## Verdict

The architecture is appropriate for the scale of the product today. The three interventions that pay for themselves:

1. Extract `RESOURCES` and `forms` from `app.py`.
2. Add an app factory (`create_app`) so functional tests are possible.
3. Deduplicate the two mutual-match query predicates.

Everything else — blueprints, background jobs, caching — is premature at this size and should stay off the roadmap until the app has 10× the routes it has today.
