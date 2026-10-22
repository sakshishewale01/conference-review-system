# ConferenceFlow

ConferenceFlow is a role-based conference paper review management system.
It provides one workflow for submitting papers, assigning reviewers,
collecting structured reviews, releasing administrator decisions, and
notifying users about important workflow events.


## What the application does

### Authors

- Register and log in securely.
- Submit a paper with a title, abstract, keywords, and PDF file.
- View their own submissions and current workflow status.
- View an official decision after an administrator releases it.
- Receive in-app notifications about submissions and decisions.

### Reviewers

- View only papers assigned to them.
- Download authorized paper files.
- Submit one structured review per assignment.
- Score technical merit, readability, originality, and relevance from 1–10.
- Provide a recommendation and review comments.
- Track pending and completed assignments.
- Receive notifications when papers are assigned.

### Administrators

- View workflow statistics and paper activity.
- Assign eligible reviewers to papers.
- Monitor pending and completed reviews.
- Inspect reviewer recommendations, scores, and comments.
- Record official `Accepted` or `Rejected` decisions.
- Release decisions after all assigned reviews are complete.
- Receive notifications when reviews are completed.

### Security and reliability

- Passwords are hashed with Werkzeug.
- Registration cannot be used to create an administrator account.
- Roles are checked on the server using database data.
- State-changing forms use session-bound CSRF protection.
- Sessions store only the user ID.
- SQL queries use parameters instead of string concatenation.
- Database connections roll back failed operations and close reliably.
- PDF uploads use generated storage names and protected downloads.
- Paper, review, decision, and notification access is authorization-checked.
- Error responses avoid exposing credentials, SQL statements, or stack traces.

## How the workflow works

1. An author creates an account and submits a PDF paper.
2. The paper is stored with a `Pending` status.
3. An administrator assigns one or more eligible reviewers.
4. Reviewers access only their assigned papers.
5. Reviewers submit structured evaluations.
6. The system tracks pending and completed reviews.
7. An administrator reviews the evaluations.
8. The administrator records and releases the official decision.
9. The author views the released decision and receives a notification.

Reviewer recommendations are advisory. They do not automatically become the
official conference decision.

## Technology stack

- **Backend:** Python and Flask
- **Database:** MySQL
- **Frontend:** HTML, Jinja templates, CSS, and JavaScript
- **Testing:** Python `unittest`
- **Development:** VS Code, Git, GitHub, and MySQL Workbench

## Project structure

```text
conference-review-system/
├── app.py                         Flask routes and workflow logic
├── db.py                          MySQL connection and transaction helpers
├── schema.sql                     Fresh-database schema
├── requirements.txt               Python dependencies
├── .env.example                   Safe configuration template
├── database/                      Reviewed, unapplied migration proposals
├── templates/                     Jinja HTML templates
├── static/                        CSS, JavaScript, and static assets
├── instance/uploads/              Local runtime PDF storage
├── tests/                         unittest regression tests
├── docs/                          Phase learning and setup documentation
├── api/index.py                   Vercel Flask entry point
└── vercel.json                    Vercel routing configuration
```

## Local setup

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example file:

```powershell
Copy-Item .env.example .env
```

Set the local Flask and MySQL values in `.env`. Never commit `.env` or place
real passwords in source code, SQL files, screenshots, or documentation.

### 4. Create the local database

Start the local MySQL service, create a development database, and apply
`schema.sql` to that database. Do not run schema files against production
without a backup and a reviewed migration plan.

### 5. Start Flask

```powershell
python app.py
```

Open `http://127.0.0.1:5000`.

The health endpoint is `http://127.0.0.1:5000/health` and returns a small
response such as:

```json
{"service": "ConferenceFlow", "status": "ok"}
```

## Testing

Run the tests without requiring a live MySQL connection:

```powershell
python -m unittest discover -s .\tests -p "test_*.py" -v
```

Compile the application and deployment entry point:

```powershell
python -m py_compile app.py db.py .\api\index.py
```

Check the working-tree diff:

```powershell
git diff --check
```

The automated tests use mocks for database-layer behavior. A separate local
MySQL environment is required for live schema and end-to-end database
integration testing.

## Database and migration status

The current design uses:

- `users`
- `papers`
- `review_assignments`
- `reviews`
- `notifications`

The repository contains migration proposals for paper ownership, decision
metadata, notifications, and database uniqueness constraints. These proposals
are not automatically executed because existing databases may contain data
that needs to be reviewed first.

Important migration files include:

- [`database/phase2_schema_migration.sql`](database/phase2_schema_migration.sql)
- [`database/phase6_decisions_notifications.sql`](database/phase6_decisions_notifications.sql)
- [`database/phase7_quality_constraints.sql`](database/phase7_quality_constraints.sql)

Never drop tables, truncate data, or apply an unreviewed migration to a
production database.

## Deployment status

The project includes a Vercel Flask entry point in
[`api/index.py`](api/index.py) and routing in [`vercel.json`](vercel.json).
This is deployment configuration, not a claim that production deployment is
complete.

Before hosting the application, configure:

- An externally reachable MySQL database.
- Secure production environment variables.
- Private, durable storage for uploaded PDFs.
- HTTPS and restricted database credentials.
- A reviewed migration and backup process.

Vercel cannot connect to MySQL running only on a developer laptop, and its
serverless filesystem is not suitable for permanently storing uploaded papers.

See [`docs/PHASE_7_DEPLOYMENT.md`](docs/PHASE_7_DEPLOYMENT.md) for the safe
deployment checklist.


## Author

**Sakshi Shewale**

B.Tech Computer Science Engineering
MIT Academy of Engineering
