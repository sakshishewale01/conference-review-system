# ConferenceFlow Phase 3: Security Setup

## Local configuration

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

Set a long random `FLASK_SECRET_KEY`. Keep `.env` local; it is ignored by
Git. Do not print its contents or commit it.

For local HTTP development:

```text
FLASK_ENV=development
FLASK_DEBUG=false
```

For a real HTTPS deployment, configure the production environment and use a
production WSGI server. The development Flask server is not a production
server.

## Install dependencies

```powershell
python -m pip install -r .\requirements.txt
```

No new Phase 3 dependency is required.

## Run tests

These tests use mocks and do not require MySQL:

```powershell
python -m unittest discover -s .\tests -p "test_*.py" -v
```

Compile the Python files:

```powershell
python -m py_compile .\app.py .\db.py .\tests\*.py
```

## Run the application

```powershell
python .\app.py
```

Open:

- `http://127.0.0.1:5000/`
- `http://127.0.0.1:5000/health`

The home and health pages do not require MySQL. Login, registration, papers,
assignments, and reviews do require a working local database.

## Security verification checklist

1. Confirm `.env` does not appear in `git status`.
2. Confirm registration cannot create an administrator.
3. Confirm POST requests without a CSRF token return `400`.
4. Confirm anonymous users are redirected from protected routes.
5. Confirm an author receives `403` from the admin dashboard.
6. Confirm uploaded files are stored under `instance/uploads`.
7. Confirm paper downloads require authentication.

## Remaining manual action

The database schema still does not contain `papers.author_id`. Do not apply
the proposed migration automatically. Inspect and repair existing data first,
then approve a separate migration procedure.
