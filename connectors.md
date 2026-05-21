# Connectors

This document describes the data connectors and external integrations used by ConvictCode.

## Database Connector

ConvictCode uses **Flask-SQLAlchemy** to connect to a relational database.

### Configuration

Set the `DATABASE_URL` environment variable in `.env`:

```
DATABASE_URL=sqlite:///felon_dating.db
```

For production, use a PostgreSQL or MySQL URL:

```
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

The connection is initialised in `app.py`:

```python
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///felon_dating.db')
db.init_app(app)
```

### Models

| Model | Table | Description |
|---|---|---|
| `User` | `users` | Registered accounts and profile data |
| `Message` | `messages` | Direct messages between users |
| `ForumPost` | `forum_posts` | Community forum posts |
| `ForumComment` | `forum_comments` | Comments on forum posts |
| `Like` | `likes` | User-to-user likes |
| `Match` | `matches` | Mutual like pairings |

All models are defined in `database.py`.

### Schema Initialisation

Tables are created automatically on startup:

```python
with app.app_context():
    db.create_all()
```

---

## Authentication Connector

**Flask-Login** manages session-based authentication.

- Session loading: `load_user(user_id)` in `app.py`
- Password hashing: `werkzeug.security` (`generate_password_hash` / `check_password_hash`)
- Unauthenticated users are redirected to `/login`

---

## Environment Configuration

**python-dotenv** loads variables from `.env` at startup.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask session signing key |
| `DATABASE_URL` | `sqlite:///felon_dating.db` | Database connection string |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `5000` | Bind port |
| `FLASK_DEBUG` | `0` | Enable debug mode (e.g., `1`, `true`, `yes`, `on`) |

Never commit `.env` to version control — it is listed in `.gitignore`.

---

## CSRF Protection

**Flask-WTF** provides CSRF token validation for submissions using `FlaskForm`. The `SECRET_KEY` environment variable is used to sign tokens. Note that routes not using `FlaskForm` (such as `add_comment`) currently lack CSRF protection — global `CSRFProtect` is not initialised in `app.py`.

---

## Production Server

**Gunicorn** is the recommended WSGI server for production deployments:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## Adding a New Connector

1. Install the package and add it to `requirements.txt`.
2. Initialise it in `app.py` after the `Flask` app is created.
3. Add any required environment variables to `.env` and document them in the table above.
