# Phase 5 Setup and Verification

## Run locally on Windows

From the repository folder:

```powershell
$env:FLASK_ENV = "development"
python -m unittest discover -s .\tests -p "test_*.py" -v
python app.py
```

Open `http://127.0.0.1:5000/` in a browser. Use test accounts in a local
development database only. Do not place real passwords in these commands or in
the repository.

## Verify the reviewer workflow

1. Create or use a local reviewer account.
2. Sign in as an administrator and assign an existing paper to that reviewer.
3. Sign in as the reviewer and open the reviewer dashboard.
4. Confirm the assignment appears with a `Pending` review status.
5. Submit one review.
6. Confirm the dashboard changes to `Completed`.
7. Try submitting the same assignment again; the application should refuse it.

The Phase 5 implementation does not apply a schema migration. Do not run
`DROP`, `TRUNCATE`, or destructive SQL, and do not point local tests at a
production database.
