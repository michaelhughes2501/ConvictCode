# 02 — Bug Hunt

## Confirmed bugs

### B1 — Windows path separator in `.gitignore`
- **File:** `.gitignore` (line 3)
- **Symptom:** `.github\instructions\codacy.instructions.md` uses `\` which Git treats as a literal on POSIX. The file is not ignored on Linux/macOS/CI.
- **Fix:** POSIX slash. **Fixed in this pass.**

### B2 — `Bodeql.yml` is a broken duplicate workflow
- **File:** `.github/workflows/Bodeql.yml`
- **Symptom:** File declares `name: "CodeQL Advanced"` — identical to the real `codeql.yml` — which causes both to appear in the Actions UI under the same name. Worse, lines 106–131 of `Bodeql.yml` glue two extra action stanzas (`SecureStackCo/actions-all-in-one@v0.1.2` and `cloudposse/github-action-auto-format@v0.12.0`) onto the last step in a way that is not valid YAML for a workflow (they are indented as sub-keys of the `Perform CodeQL Analysis` step). CodeQL happens to still start because the file registers the earlier valid jobs; the tail is silently ignored. But any attempt to touch the file will hit a parser error.
- **Fix:** Delete. `codeql.yml` covers the same three languages (`actions`, `javascript-typescript`, `python`). **Fixed in this pass.**

### B3 — `User.password_hash` is `VARCHAR(128)` — too short for scrypt
- **File:** `database.py:14`
- **Symptom:** `password_hash = db.Column(db.String(128), nullable=False)`. Werkzeug's default hasher on 2024+ releases is scrypt, which produces hashes of ~135–170 chars. SQLite ignores the length limit; **PostgreSQL and MySQL enforce it**. On those databases, `set_password` inserts a truncated hash, `check_password_hash` compares the truncated stored value against a full-length hash and returns False, and every login fails.
- **Fix:** Change to `db.String(255)` or `db.Text`. Requires a migration on live databases (no migration tool wired here; `db.create_all()` won't alter existing tables). **Not applied in this pass** — a column-width change to a hashed-password column is a schema change that needs a migration, not an ad-hoc code edit. Called out prominently in [07-refactor-plan.md](./07-refactor-plan.md).

### B4 — `view_post` increments views without auth, rate-limit, or atomic UPDATE
- **File:** `app.py:260–266`
- **Symptom:** Anonymous `GET /forum/post/<id>` reads `post.views`, adds 1, writes it back. Two concurrent requests both read the same value and both write value+1, losing an increment.
- **Fix:** Use `ForumPost.query.filter_by(id=post_id).update({'views': ForumPost.views + 1})` for an atomic SQL-side increment; consider rate-limiting anonymous access. Not applied — behavioural change.

### B5 — `datetime.utcnow()` is deprecated on Python 3.12+
- **Files:** `app.py:131, 366, 367`; `database.py:38, 68, 82, 83, 98, 108, 119`.
- **Symptom:** Deprecation warning today; slated for removal in Python 3.15. Deprecated because it returns a naive datetime that looks UTC but has no tzinfo — a genuine source of bugs when compared to aware timestamps.
- **Fix:** Replace with `datetime.now(timezone.utc)` (import `timezone`). Not applied — it's a cross-file mechanical rewrite that should be its own PR with test coverage.

### B6 — `Match.is_mutual == True` filter uses `== True` instead of `.is_(True)`
- **File:** `app.py:144, 284`; `analytics` at line 372.
- **Symptom:** Works today because SQLAlchemy generates `is_mutual = 1` for SQLite. On stricter dialects and with `flake8-sqlalchemy`, `== True` is flagged as an anti-pattern. Also breaks if `is_mutual` becomes tri-state (True / False / NULL).
- **Fix:** `Match.is_mutual.is_(True)`. Not applied — behavioural equivalence on current SQLite; cosmetic.

## Latent bugs

### L1 — `conversation` marks messages read before validating the form
- **File:** `app.py:222–224`
- **Symptom:** A GET request to `/messages/<user_id>` marks all inbound messages from that user as read. That is intended for the page-visit case. But a request with query string `?next=...` in an attempt to bounce through this route still triggers the read-marker. Low severity; noted for completeness.
- **Fix:** Either accept it as by-design or move the update inside `if request.method == 'GET':`.

### L2 — `search` route: LIKE metacharacters passed through
- **File:** `app.py:300–311`
- **Symptom:** `User.username.contains(query)` renders `WHERE username LIKE '%<query>%'`. A user searching for `%_` will match every row. Not a security bug, but a UX and perf smell.
- **Fix:** `escape` the query with the SQL LIKE-escape character before `.contains()`. Not applied.

### L3 — `messages` route builds conversation list per user in an N+1 loop
- **File:** `app.py:206–214`
- **Symptom:** For each unique `uid`, it issues two queries: `User.query.get(uid)` and a filtered `Message.query`. With 50 conversations that's 100 queries per page render.
- **Fix:** Batch load users with `User.query.filter(User.id.in_(user_ids))`, and derive last-message + unread-count in a single grouped query. Not applied — perf smell, not a correctness bug.

### L4 — `login` writes `user.last_login = datetime.utcnow()` after `login_user()`
- **File:** `app.py:130–132`
- **Symptom:** `login_user(user)` commits its own session bookkeeping; then this code sets `last_login` and commits. If the second commit fails, the user is logged in but `last_login` is stale. Recovery is trivial (next login fixes it), so this is a soft bug.
- **Fix:** Set `last_login` *before* `login_user`, in the same session, and commit once. Not applied.

### L5 — `chat` swallows all exceptions silently
- **File:** `app.py:355–360`
- **Symptom:** `except Exception:` masks bad API keys, rate limit hits, model name typos, and quota-exceeded errors — the user always sees the canned "I'm here to help!" reply. Debugging the outage requires SSHing into the box and reading logs (which don't include the exception either).
- **Fix:** `except anthropic.APIError as e: app.logger.exception('anthropic chat failure')` — narrower except type + logging.

### L6 — `SECRET_KEY` default lets the app start in production with `dev-secret-key-change-in-production`
- **File:** `app.py:15`
- **Symptom:** Nothing verifies the value at boot. In a Kubernetes / Fly / Render deploy where env vars are set in a dashboard, a missing var means the default takes over and session cookies are trivially forgeable.
- **Fix:** In `if __name__ == '__main__':` or (better) at module load time, refuse to start if `os.getenv('SECRET_KEY')` is None *and* `FLASK_DEBUG` is not truthy. Not applied — a boot-refusal change should ship with the rest of the security hardening in one PR.

### L7 — `/api/analytics` leaks growth metrics to any authenticated user
- **File:** `app.py:363–376`
- **Symptom:** Only `@login_required`, not admin-gated. Any registered user learns total users, total messages, weekly new-user count.
- **Fix:** Add an `is_admin` field to `User` (or a `role` column matching the sibling `remix-the-yard` pattern) and gate the route with a decorator. Not applied — schema change + policy decision.

## Not-a-bug

- **`view_profile` at line 166** — exposes `crime_type`, `release_date`, `rehabilitation_status` to any authenticated user. This is *intentional* for a dating app and matches the design in `templates/view_profile.html`. Flagged in [04-security-review.md](./04-security-review.md) as a privacy consideration, not a bug.
- **CSRF exemption on `/api/chat`** — correct per `connectors.md`; the route requires `@login_required` and is JSON-only. Adding a strict Origin header check would be defence-in-depth, not a bug fix.

## Nothing else surfaced from a static read

Route logic is largely straightforward CRUD. No obvious IDOR (routes filter by `current_user.id` or use `.get_or_404`). No obvious SSRF (no outbound HTTP to user-controlled URLs). Template auto-escape is respected; no `|safe` on user data. If functional tests existed, this file could be shorter — the lack of them is why the L-tier bugs are all suspicions rather than reproductions.
