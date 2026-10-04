# 05 — Production-Readiness Review

## Ready-to-ship checklist

| # | Requirement | State |
|---|-------------|-------|
| 1 | Reproducible install | Partial — `requirements.txt` has upper caps; no lockfile (`pip-tools` / `uv` / `pip-compile` output). |
| 2 | Env config documented + enforced | Docs OK (`.env.example`, `connectors.md`). No boot-time enforcement. |
| 3 | Dependencies audited | No `pip-audit` / Dependabot for `pip`. |
| 4 | Minimum test bar | 5 doc-consistency test modules. **Zero functional route tests.** |
| 5 | CI enforcing tests | CodeQL runs but does not run tests. No `pytest` job. |
| 6 | Observability | None — no structured logging, no APM, no error reporter. |
| 7 | Rate limiting | None. |
| 8 | Security headers (CSP, HSTS, XFO) | None. |
| 9 | Backup / restore plan | None documented; `instance/felon_dating.db` is SQLite and unbacked-up. |
| 10 | Migrations | None — `db.create_all()` on startup only. Column changes not applied. |
| 11 | Admin surface | None — no admin user, no ban / moderate tooling. |
| 12 | Runbook | Absent. |
| 13 | GDPR / data-deletion path | Absent. |

## Deployment configuration

### What exists
- `SECURITY.md`, `CLAUDE.md`, `connectors.md`, `.env.example`, and a documented `gunicorn -w 4 -b 0.0.0.0:5000 app:app` command.

### What's missing for a real deploy
- **A `Dockerfile`.** For a Python + Flask app with CDN-heavy templates, this is a 20-line file. Ship one.
- **A `.dockerignore`.** Otherwise `venv/`, `instance/`, and `__pycache__/` bloat the image.
- **A `Procfile` (Heroku/Render/Fly)** OR a `render.yaml` OR a `fly.toml`. Pick a target and commit the config.
- **A managed database.** SQLite is fine for dev; the `instance/felon_dating.db` file is not survivable across restarts on ephemeral hosts (Fly, Heroku dynos, most Kubernetes pods). Provision Postgres (Supabase, Neon, RDS) and set `DATABASE_URL`.
- **A migration story.** Once Postgres is in play, `db.create_all()` will not alter columns — even something as basic as widening `password_hash` (see [02-bug-hunt.md#b3](./02-bug-hunt.md)) requires Alembic. Add `Flask-Migrate`.

## Observability

Nothing exists today. Minimum viable stack for a Flask app:

1. **Structured logging** — replace Flask's default logger with one that emits JSON to stdout (`python-json-logger`). Every log line includes request-id, user-id, route, status, and duration.
2. **Error reporter** — Sentry is the obvious choice. `sentry-sdk[flask]` is a one-line init. Free tier is generous.
3. **Uptime probe** — a public `/health` endpoint that returns `{"status": "ok"}` and does a lightweight DB `SELECT 1`. UptimeRobot or Better Uptime hits it every minute. No such endpoint exists today.
4. **Request logging** — gunicorn's `--access-logfile -` sends access logs to stdout. Wire it into the production command in `Procfile` / systemd unit.

## Data lifecycle

- **Backup** — nothing. On a managed Postgres, provider snapshots are the baseline. Document the retention and restore procedure.
- **Restore** — see above; needs a documented test-restore cadence.
- **Data deletion** — `User.query.get(uid).delete()` cascades to `ForumComment` (via `cascade='all, delete-orphan'` on `ForumPost.comments`) but does NOT cascade to `Message`, `Like`, `Match`, or `ForumPost`. A deleted user leaves orphan records with a dangling `user_id` foreign key. GDPR-wise, "delete my account" is not a solved problem here.
- **PII inventory** — not documented. Needed for any privacy policy.

## Reliability

- **No graceful shutdown.** Gunicorn handles SIGTERM but the app's `chat` handler makes an outbound HTTP call to Anthropic that can hang for tens of seconds; a naive SIGTERM will interrupt in-flight requests.
- **No timeout on the Anthropic call.** `client.messages.create(...)` uses SDK defaults (~60s). During an Anthropic incident, every chat request pins a worker for the full timeout, exhausting the four gunicorn workers under trivial load.
- **No circuit breaker.** If Anthropic is degraded, the app keeps trying every request. Cheap fix: `circuitbreaker` PyPI package.

## Documentation

- **CLAUDE.md** — comprehensive, in-sync with the code as of this pass.
- **SECURITY.md** — exists.
- **connectors.md** — exists and is test-enforced. Excellent.
- **README.md** — need to verify; not covered here.
- **CHANGELOG.md** — absent. For a public product, add one.
- **Runbook** — absent. Even a single-page markdown describing "how to reset a user's password", "how to purge a spam thread", "how to bump anthropic model", "how to add an admin user" would be a real improvement.

## Verdict

The app is functionally complete for a demo but production-fragile. The gap list is on the order of one focused week of work: Dockerfile + Procfile, managed Postgres + Alembic + widen password_hash, structured logs + Sentry, rate limits + Talisman, functional tests + CI, admin gate + backup runbook. None of these are large individually; skipping any one of them makes the launch reckless.
