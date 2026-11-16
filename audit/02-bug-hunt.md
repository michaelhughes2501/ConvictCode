# 02 — Bug Hunt

## Confirmed bugs

### B1 — Windows path separator in `.gitignore` (and the file is already tracked)
- **File:** `.gitignore` (line 2)
- **Symptom:** `.github\instructions\codacy.instructions.md` used `\` which Git treats as a literal on POSIX, so the entry was a no-op on Linux/macOS/CI. The POSIX-slash fix was applied in this pass — but `.github/instructions/codacy.instructions.md` is **already tracked in the index**, so the ignore pattern still has no effect on the file today. Gitignore rules only apply to *untracked* paths; once a path is tracked, `.gitignore` cannot suppress its `git status` entries when the file is modified, and `git add -A` continues to pick up its edits.
- **Fix:** POSIX slash **applied in this pass.** To actually stop tracking the Codacy instructions file, a follow-up PR must run `git rm --cached .github/instructions/codacy.instructions.md` and commit the removal. Not applied here — untracking is a deliberate policy decision about whether these instructions should live in the repo at all.

### B2 — `Bodeql.yml` is a broken duplicate workflow
- **File:** `.github/workflows/Bodeql.yml`
- **Symptom:** File declares `name: "CodeQL Advanced"` — identical to the real `codeql.yml` — so both appeared in the Actions UI under the same name. Lines 106–131 glued two extra action stanzas (`SecureStackCo/actions-all-in-one@v0.1.2` and `cloudposse/github-action-auto-format@v0.12.0`) onto the last step with indentation that is not valid workflow YAML. GitHub rejects the whole file as a parse failure before scheduling any job from it, so none of its CodeQL steps actually ran — the duplicate name was the only visible symptom, and CodeQL coverage came entirely from the real `codeql.yml`.
- **Fix:** Delete. `codeql.yml` covers the same three languages (`actions`, `javascript-typescript`, `python`). **Fixed in this pass.**

### B3 — `User.password_hash` is `VARCHAR(128)` — too short for scrypt
- **File:** `database.py:14`
- **Symptom:** `password_hash = db.Column(db.String(128), nullable=False)`. Werkzeug's default hasher on 2024+ releases is scrypt, which produces hashes of ~135–170 chars. SQLite ignores the length limit so dev is fine. On **PostgreSQL** the over-length value raises `psycopg2.errors.StringDataRightTruncation` (`DataError`) at insert time, so `/register` fails outright and no account is created — the current column already breaks registration on Postgres today. On **MySQL** the behaviour depends on `sql_mode`: strict mode errors on insert (same failure as Postgres), non-strict mode silently truncates and then every `check_password_hash` call returns False against the full-length hash on login. Either way, moving the database from SQLite surfaces the bug.
- **Fix:** Change to `db.String(255)` or `db.Text`. Requires a migration on live databases (no migration tool wired here; `db.create_all()` won't alter existing columns). **Not applied in this pass** — a column-width change to a hashed-password column is a schema change that needs a migration, not an ad-hoc code edit. Called out prominently in [07-refactor-plan.md](./07-refactor-plan.md).

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
- **Symptom:** Stylistic only — `== True` is flagged by `flake8-sqlalchemy` as an anti-pattern. SQLAlchemy emits a valid boolean predicate on both SQLite and Postgres, and `== True` and `.is_(True)` both exclude NULL rows the same way. No cross-dialect or tri-state correctness difference; pure style.
- **Fix:** `Match.is_mutual.is_(True)` if adopting the linter. Not applied — stylistic, no behavioural difference.

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
- **Symptom:** For each unique `uid`, it issues three queries: `User.query.get(uid)`, the last-message `Message.query` (ordered by `created_at desc` + `first()`), and the unread `Message.query.filter(...).count()`. With 50 conversations that's 150 queries per page render.
- **Fix:** Batch load users with `User.query.filter(User.id.in_(user_ids))`, and derive last-message + unread-count in a single grouped query. Not applied — perf smell, not a correctness bug.

### L4 — `login` can set Flask's session cookie before the DB commit succeeds
- **File:** `app.py:130–132`
- **Symptom:** The route calls `login_user(user)` (which writes authentication state into Flask's signed session) *before* setting `user.last_login` and calling `db.session.commit()`. There is only one commit — the earlier "two commits" framing in draft notes was wrong; `login_user()` does not touch the DB session. The soft bug: if that single commit raises, the user has already been marked authenticated in the Flask session and the error response can still carry a Set-Cookie with the authenticated session, while `last_login` was never persisted.
- **Fix:** Move the `last_login` write and `db.session.commit()` **before** `login_user(user)`, so a DB failure aborts the login attempt rather than leaving authenticated session state attached to the error response. Not applied — small behavioural change worth doing alongside the login hardening in the refactor plan.

### L5 — `chat` swallows all exceptions silently
- **File:** `app.py:355–360`
- **Symptom:** `except Exception:` masks bad API keys, rate limit hits, model name typos, and quota-exceeded errors — the user always sees the canned "I'm here to help!" reply. Debugging the outage requires SSHing into the box and reading logs (which don't include the exception either).
- **Fix:** Guard the missing-key case first (`if not os.getenv('ANTHROPIC_API_KEY'): return canned_fallback`), then build the client, then catch `anthropic.APIError` narrowly with `app.logger.exception('anthropic chat failure')`. If the except is narrowed to `APIError` without the missing-key guard, `anthropic.Anthropic(api_key=None)` raises outside that handler and `/api/chat` returns a 500 instead of the fallback — the current broad except accidentally covers this today. Not applied.

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

### L8 — `like_user` and `add_comment` don't verify the target exists
- **Files:** `app.py` (like route around line 183; comment route around line 275).
- **Symptom:** `like_user(user_id)` creates a `Like` row and possibly a `Match` without a `User.query.get_or_404(user_id)` check — a crafted POST to `/like/<nonexistent-id>` writes an orphan `Like` whose `liked_user_id` FK points at nothing. `add_comment(post_id)` has the same shape for `ForumComment`. On SQLite FK enforcement is off by default so the orphan rows persist; on Postgres with FKs enforced, the insert errors and 500s.
- **Fix:** `User.query.get_or_404(user_id)` / `ForumPost.query.get_or_404(post_id)` at the top of each handler, before writing. Not applied.

## Not surfaced here but worth a note

Route logic is largely straightforward CRUD. No obvious IDOR (routes filter by `current_user.id` or use `.get_or_404`). No obvious SSRF (no outbound HTTP to user-controlled URLs). Template auto-escape is respected; no `|safe` on user data. If functional tests existed, this file could be shorter — the lack of them is why the L-tier bugs are all suspicions rather than reproductions.
