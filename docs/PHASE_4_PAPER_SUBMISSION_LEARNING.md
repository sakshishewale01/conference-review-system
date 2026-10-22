# ConferenceFlow Phase 4: Paper Submission and Documents

## The submission flow

1. An authenticated author opens `/submit_paper`.
2. The browser displays an HTML form with title, abstract, keywords, and a
   PDF file input.
3. The form includes a CSRF token and sends a `POST` request.
4. Flask validates text lengths, the extension, the filename, and the request
   size.
5. Flask generates a random storage filename instead of trusting the original
   filename.
6. The file is stored under `instance/uploads`, outside the public static
   directory.
7. Flask inserts the metadata into MySQL using a parameterized query.
8. The server commits the database operation and redirects to `/papers`.

This is Post/Redirect/Get: after a successful POST, the browser receives a
redirect instead of rendering the POST response directly. Refreshing the
result page therefore does not normally resubmit the form.

## Validation

The server is the authority. Browser attributes such as `required`,
`minlength`, and `accept` improve the user experience but cannot replace
server-side validation.

Current limits:

- Title: 5 to 255 characters
- Abstract: 50 to 10,000 characters
- Keywords: required, up to 1,000 characters
- Upload: PDF extension, up to 10 MB

The database schema currently stores the original display name in
`file_name` and the generated storage path in `uploaded_file_path`.

## Why filenames are untrusted

A filename can contain path traversal characters, duplicate another user's
file, or have a misleading extension. `secure_filename()` removes unsafe
characters, and the application then ignores that name for storage and uses a
random generated PDF filename.

The browser MIME type is not treated as proof that a file is a valid PDF.
This project does not claim malware scanning or complete document-content
verification.

## Secure downloads

The paper list links to:

```text
/papers/<paper_id>/download
```

The route requires authentication, loads the database path by parameterized
paper ID, checks the resolved path against approved upload directories, and
only then calls `send_file()`.

Reviewers can download papers assigned to them. Administrators can download
papers. Anonymous users are rejected.

The current schema does not contain `papers.author_id`, so the application
cannot prove that an author owns a historical paper. Full author ownership
requires the unapplied migration documented in
[database/phase2_schema_migration.sql](../database/phase2_schema_migration.sql).

## Paper statuses

New submissions receive `Pending` on the server. Existing workflow statuses
are:

- `Pending`
- `Under Review`
- `Accepted`
- `Rejected`

Authors do not submit a status field and cannot set a privileged status.
Reviewer assignment changes a paper to `Under Review`. Status changes by
administrators should be implemented as a separate controlled action rather
than changed when a page is viewed.

## Failure and cleanup

The file is written before the database insert because the database stores its
path. If the insert fails, the newly created file is removed when safe to do
so. Existing files are never removed by this workflow.

Database operations use the Phase 2 cursor and connection scopes. A failed
transaction is rolled back and resources are closed.

## What remains limited

The current schema cannot associate a paper with its submitting author.
Therefore, author-specific paper lists, edits, and downloads cannot be
claimed as fully enforced. Do not guess historical owners. Apply a reviewed
local migration only after inspecting existing data.
