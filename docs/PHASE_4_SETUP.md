# ConferenceFlow Phase 4: Paper Submission Setup

## Install and test

From the repository root:

```powershell
python -m pip install -r .\requirements.txt
python -m unittest discover -s .\tests -p "test_*.py" -v
```

Compile the Python files:

```powershell
$files = @('app.py','db.py') + (Get-ChildItem .\tests -Filter '*.py' -File | ForEach-Object { $_.FullName })
python -m py_compile $files
```

## Configure local environment

```powershell
Copy-Item .env.example .env
```

Set local values in `.env`. Never print or commit this file.

## Upload storage

The application creates:

```text
instance\uploads\
```

The directory is ignored by Git through the `instance/` rule. Existing files
under `static\uploads\` are preserved and are not automatically moved or
deleted.

## Run the application

```powershell
python .\app.py
```

Open `http://127.0.0.1:5000/`, register as an author, and submit a PDF using
the form. MySQL must be running for registration and paper submission.

## Safe schema migration procedure

The current schema has no paper-owner field. The proposed migration is
commented out in:

```text
database\phase2_schema_migration.sql
```

Do not run it automatically. First confirm that the target is a local
development database, inspect existing rows, decide how ownerless historical
papers will remain ownerless, and back up important data. Never run migration
SQL against production without a reviewed deployment procedure.

## Manual verification

1. Submit a PDF shorter than 10 MB.
2. Confirm the list shows `Pending`.
3. Open the paper details page.
4. Confirm the browser uses the authenticated download route.
5. Try an HTML file and confirm it is rejected.
6. Submit without a CSRF token and confirm `400`.
7. Confirm no upload path is shown in the page HTML.
