# ConferenceFlow Phase 3: Security Learning Guide

## Authentication and authorization

Authentication answers: "Who is this user?" ConferenceFlow authenticates a
user by finding the normalized email and verifying the submitted password
against the stored Werkzeug password hash.

Authorization answers: "What may this user do?" The `role_required()` helper
checks the authoritative role from the database before allowing access to
administrator, author, or reviewer routes.

The browser must never be trusted to choose its own role. Registration always
creates an `author`; the submitted `role` field is ignored.

## Passwords and sessions

The database stores a password hash, not the original password. A successful
login clears any previous session data and stores only `user_id`. The role
and account details are loaded from the database when authorization is needed.

The session cookie is configured with:

- `HttpOnly`, so JavaScript cannot read it;
- `SameSite=Lax`, reducing cross-site request risks;
- `Secure` in production, when the application is configured for production
  HTTPS.

## CSRF protection

CSRF means a malicious site tricks a logged-in browser into submitting a
state-changing request. ConferenceFlow creates a random token in the session,
places it in forms, and compares the submitted token with
`secrets.compare_digest()` before accepting POST requests.

The token protects registration, login, logout, paper submission, assignment,
and review submission.

## Authorization in this project

The server protects routes; hiding a navigation link is not security.

- Authors can submit papers.
- Administrators can view dashboard metrics, list reviewers, and assign
  reviewers.
- Reviewers can view their assignments and submit reviews.
- Authenticated users can view the paper list.

The current schema has no paper-owner column. Therefore, Phase 3 does not
claim full author ownership enforcement. A reviewed schema migration adding
`papers.author_id` is still required for that guarantee.

## Secure uploads

Uploads are checked for a non-empty filename and a `.pdf` extension. Files
are stored with a generated random filename under `instance/uploads`, outside
the public static directory, and the original filename is kept in the
database for display.

The protected download route verifies that the database path is inside an
approved upload directory before calling `send_file()`. Existing legacy
files under `static/uploads` remain for compatibility but should be moved
through a reviewed maintenance procedure.

Extension checks are not malware scanning. They reduce common mistakes but
do not prove that a file is safe PDF content.

## Database error handling

Database routes use the Phase 2 cursor and connection scopes. Errors trigger
rollback and cleanup, while users receive generic responses. Logs record the
exception type rather than SQL parameters, passwords, or stack traces.

## Important limitation

The current schema cannot identify a paper's author. This prevents complete
ownership authorization. Do not describe author-only paper access as fully
implemented until the `author_id` migration is safely applied and tested.
