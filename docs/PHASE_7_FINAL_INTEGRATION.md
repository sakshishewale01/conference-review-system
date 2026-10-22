# ConferenceFlow Phase 7: Final Integration and Quality Assurance

## What was inspected

The final pass reviewed the Flask routes, authentication and role checks,
database context managers, schema, templates, static assets, tests, migration
proposals, environment configuration, and deployment files.

The application is a server-rendered Flask application. `app.py` owns routes
and workflow rules, `db.py` owns MySQL connection cleanup and rollback, Jinja
templates render the UI, and `instance/uploads` stores local uploaded PDFs.

## Fixes completed

- Added an explicit safe JSON 404 response.
- Added quality regression tests for health, 404, and logout method handling.
- Added fresh-schema uniqueness and non-null constraints for reviewer
  assignments and reviews.
- Added an unapplied migration proposal for those constraints on existing
  databases.
- Added a minimal Vercel Flask entry point and configuration.
- Preserved environment-based secrets, CSRF validation, role authorization,
  parameterized SQL, upload path checks, and database rollback behavior.

## Security decisions

- Registration always creates an `author`; a submitted role is ignored.
- Administrative routes query the role from the database rather than trusting
  the session or browser.
- Paper and review access is checked server-side.
- State-changing requests require the session-bound CSRF token.
- Session cookies are HttpOnly and use SameSite=Lax.
- Uploaded files use generated names, PDF allowlisting, and protected
  downloads.
- Notifications are queried and updated using the authenticated recipient ID.
- Error responses do not return SQL, credentials, stack traces, or tokens.

## Test result

Run:

```powershell
python -m unittest discover -s .\tests -p "test_*.py" -v
python -m py_compile app.py db.py .\api\index.py
git diff --check
```

The test suite is expected to run without MySQL because the database-layer
tests use mocks. Live schema and workflow integration still require a safe
local MySQL database.

## Deployment limitations

Vercel can import the Flask application through `api/index.py`, but it cannot
reach a MySQL server running only on a developer laptop. Vercel's filesystem
is also ephemeral, so `instance/uploads` is not durable storage for submitted
papers. Production deployment therefore requires externally reachable MySQL
and durable private document storage, plus corresponding application changes.

Do not describe the current Vercel configuration as a complete production
deployment. No external service was contacted or deployed by this phase.

## Remaining limitations

- The Phase 6 migration and Phase 7 constraint migration are not applied.
- Historical paper ownership requires a reviewed backfill.
- Decision history is not stored in a separate audit table.
- Email and browser push notifications are not implemented.
- Live MySQL integration and upload persistence in a hosted environment remain
  deployment tasks.
