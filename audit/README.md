# Engineering Audit — ConvictCode / SecondChance Connect

Branch: `claude/engineering-audit-refactor-j2mphk`
Scope: Phase 1 — reports + safe fixes only. Refactor execution deferred.

## Context

ConvictCode is a Flask 2.3 web app (~400 LOC in `app.py`, ~120 LOC in `database.py`, 12 Jinja2 templates). Auth via Flask-Login, ORM via Flask-SQLAlchemy, CSRF via Flask-WTF, chatbot via the `anthropic` SDK. Deployed with gunicorn. Tests exist but only verify `connectors.md` matches the source — no functional tests for routes.

## Reports

| # | File | Focus |
|---|------|-------|
| 1 | [01-deep-engineering-audit.md](./01-deep-engineering-audit.md) | Snapshot of engineering quality |
| 2 | [02-bug-hunt.md](./02-bug-hunt.md) | Concrete confirmed + latent defects |
| 3 | [03-dependency-audit.md](./03-dependency-audit.md) | requirements.txt review, upgrade path |
| 4 | [04-security-review.md](./04-security-review.md) | Auth, CSRF, secrets, PII, rate-limiting |
| 5 | [05-production-readiness.md](./05-production-readiness.md) | Deploy, observability, backup, docs |
| 6 | [06-architecture-review.md](./06-architecture-review.md) | Single-file app vs blueprints, layering |
| 7 | [07-refactor-plan.md](./07-refactor-plan.md) | Ordered PRs to reach the target state |
| 8 | [08-fixed-project-structure.md](./08-fixed-project-structure.md) | Target tree after refactor |

## Safe fixes applied in this pass

- **`.gitignore`** — replaced the Windows-typed `.github\instructions\codacy.instructions.md` rule (a no-op on POSIX / CI) with a POSIX path.
- **`.github/workflows/Bodeql.yml`** — deleted. The file was a broken/duplicate copy of `codeql.yml`: same workflow name (so it clashed with the real one in the Actions UI), plus two malformed action stanzas (SecureStack + cloudposse) glued to the bottom that would have failed to parse if the workflow ever ran. `CLAUDE.md` had already flagged this as a known TODO ("The `Bodeql.yml` workflow is a typo of `CodeQL.yml` and likely redundant with `codeql.yml`").
- **`CLAUDE.md`** — removed the now-resolved `Bodeql.yml` line from the "Known TODOs" list.

Everything else is left as a proposal in the reports so it can be reviewed before being executed.
