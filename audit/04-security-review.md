# 04 — Security Review

## Authentication

### Strengths
- **Password hashing** via `werkzeug.security.generate_password_hash` (scrypt by default on modern Werkzeug). Salt is per-user; comparison is timing-safe inside `check_password_hash`.
- **Session cookies** signed with `SECRET_KEY`, HTTP-only by default in Flask.
- **`load_user` is defensive** — non-numeric user-id cookies don't crash.
- **`login_required`** on every non-public route in the app.

### Gaps
- **`password_hash` column is `VARCHAR(128)`** (see [02-bug-hunt.md#b3](./02-bug-hunt.md)). Scrypt hashes exceed 128 chars; on PostgreSQL / MySQL logins would silently fail. **Sev: high on non-SQLite backends.**
- **No account lockout / brute-force protection.** Login is unrate-limited; a script can guess passwords indefinitely. `Flask-Limiter` is not installed.
- **No email verification flow.** `User.is_verified = Boolean(default=False)` exists in the schema but nothing sets it; anyone can register and immediately act.
- **No password strength requirement** beyond `Length(min=6)`. Six characters is well below any 2020s baseline; recommend `Length(min=10)` plus a common-password blacklist (`have-i-been-pwned`-style check, or a static top-10k blacklist).
- **`SECRET_KEY` has a weak default** (`dev-secret-key-change-in-production`) and no boot-time enforcement. See [02-bug-hunt.md#l6](./02-bug-hunt.md).

## CSRF

- **`CSRFProtect(app)` is initialised globally** on line 20 — protects every POST by default, including `add_comment` (which uses `request.form.get` directly). This is the correct and safest wiring.
- **One documented exemption:** `/api/chat` via `@csrf.exempt`, because it is a JSON API called from `fetch()`. That combination — JSON body + `@login_required` — makes CSRF a limited threat, but adding a same-origin check (validate `Origin`/`Referer` header) is a cheap defense-in-depth. Deferred.
- **CSRF error handler** returns a redirect and flashes a friendly message; no info leak.

## Input validation

- **WTForms** validators enforce length and presence on every form-backed route.
- **`add_comment` does not validate content length** (no `Length(max=...)`). A user can post a multi-MB comment and it will land in the DB. **Sev: medium.** Deferred; fix is `Length(max=2000)` plus a corresponding `<textarea maxlength="...">`.
- **`chat` route trims whitespace but does not cap length** on `user_message`. Anthropic will reject very long inputs, but the app pays for the trip. Cap at ~2000 chars before dispatching.

## Output escaping

- **Jinja2 auto-escapes** all `{{ ... }}` interpolations. No `|safe` filter is used on user data (checked `templates/`).
- **CSP header:** none set — see below.

## Authorisation

- **`/api/analytics` is not admin-gated.** Any authenticated user can pull growth metrics. **Sev: medium.** See [02-bug-hunt.md#l7](./02-bug-hunt.md).
- **No admin role at all** — there is no `is_admin` / `role` column on `User`. Moderation of forum posts, deletion of users, ban-hammer for abusive DMs: none of it exists. Compare to `remix-the-yard` which has a four-tier role system.
- **IDOR audit:** routes that accept a user-id path parameter (`view_profile`, `conversation`, `like_user`) do compare against `current_user.id` where relevant, so a user can't like themselves or read another user's conversation. Correct.

## PII / sensitive data

- **`crime_type`, `release_date`, `rehabilitation_status`** are shown to any authenticated user via `view_profile`. This is intentional for a felony-focused dating app but it is **the most sensitive field in the schema** — a data breach of `users` reveals conviction history for every account. Recommendation: encrypt at rest, or store category buckets only (`Nonviolent` / `Violent` / etc.) rather than free-text `crime_type`.
- **No PII scrubbing** in messages. A user can send another user's SSN or credit card number in a DM and it lands in the DB in plaintext. Sibling `new-horizon-platform` has `fn_scrub_pii()` for exactly this — worth porting.
- **Audit log:** none. If an account is compromised, there's no way to prove what actions were taken. Consider a `security_events` table (again, mirror `new-horizon-platform`).
- **Data-at-rest:** SQLite dev file `felon_dating.db` sits in `instance/`. Anyone with disk access reads it. In production the recommendation is a managed PostgreSQL with encryption-at-rest turned on (Neon, Supabase, RDS all do this by default).

## Transport & headers

- **No HSTS.** Anyone MITM'ing a downgraded HTTP hop can strip auth.
- **No CSP.** With `base.html` loading Bootstrap and Font Awesome from jsdelivr and cdnjs, plus its own inline `<script>` for the theme flash-of-unstyled-content fix, a strict CSP needs `script-src 'self' 'unsafe-inline'` (or, better, replace the inline script with a hashed one). Recommendation: `Flask-Talisman` with:
  ```python
  csp = {
      'default-src': "'self'",
      'style-src':   ["'self'", 'cdn.jsdelivr.net', 'cdnjs.cloudflare.com'],
      'script-src':  ["'self'", 'cdn.jsdelivr.net', "'unsafe-inline'"],  # or use SRI + hash
      'font-src':    ["'self'", 'cdnjs.cloudflare.com', 'data:'],
      'img-src':     ["'self'", 'data:'],
  }
  ```
- **No SRI on the CDN links** in `base.html`. If jsdelivr is compromised, every page ships hostile CSS. Add `integrity=` + `crossorigin="anonymous"`.
- **`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`:** none. Talisman sets sane defaults for all three.

## AI-specific concerns (`/api/chat`)

- **Prompt injection:** the system prompt is fixed in code, but nothing filters user input for injection ("Ignore previous instructions and tell me..."). This is a shared industry challenge; the important thing is that the chatbot has **no tool access**, does not touch the DB, and cannot exfiltrate data — its output is only shown to the user who sent the message. Sev: low.
- **PII in prompts:** any message the user types is sent to Anthropic. Compliance-wise, this needs to be disclosed in a privacy policy (`SECURITY.md` does mention it obliquely).
- **Rate limiting:** none. A malicious user can drain your Anthropic budget. **Sev: high on cost.** Recommend a per-user cap (e.g. 30 messages/hour, 300/day) via `Flask-Limiter`.
- **Cost tracking:** no metering. Recommend logging `response.usage.input_tokens` + `output_tokens` per call to a table so cost can be attributed.

## Dependency-level

- **`bcrypt` is declared but unused.** Not a vulnerability, but reduces the attack surface if removed. See [03-dependency-audit.md](./03-dependency-audit.md).
- **`Pillow` is declared but unused.** Same.

## Static analysis

- **CodeQL Advanced** runs on push/PR against `main` and weekly. Covers Actions + JS/TS + Python. Good.
- **Microsoft Defender for DevOps** also runs. Good; overlap with CodeQL is fine.
- **`Bodeql.yml` was a broken duplicate CodeQL workflow** — deleted in this pass.
- **No `pip-audit` / `safety` step** — see [03-dependency-audit.md](./03-dependency-audit.md).

## Summary

Zero exploitable issues in the code today *if* the DB is SQLite and no one guesses the login password. Real production launch needs, in priority order:

1. Widen `password_hash` column (B3) — without this, PG/MySQL migration breaks login.
2. Rate-limit `/login`, `/register`, `/api/chat`.
3. Admin-gate `/api/analytics`.
4. Boot-refuse on the default `SECRET_KEY` outside dev.
5. Add Talisman + SRI + CSP.
6. Sanitise / encrypt `crime_type`.
7. Add password strength + email verification.
