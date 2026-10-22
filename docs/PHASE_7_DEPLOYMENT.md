# ConferenceFlow Deployment Readiness

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Set real values only in the untracked `.env` file. Never copy passwords into
PowerShell history, source files, SQL files, or documentation.

## Vercel configuration

The repository contains `api/index.py` and `vercel.json`. Vercel environment
variables must provide `FLASK_SECRET_KEY`, `MYSQL_HOST`, `MYSQL_PORT`,
`MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE`.

The database host must be reachable from Vercel. `localhost` refers to the
serverless runtime itself, not the developer's computer.

## Important hosting limitations

- The local `instance/uploads` directory is not durable on Vercel.
- Uploaded PDFs need private object storage or another durable storage
  service before hosted deployment.
- MySQL must be hosted or network-accessible with TLS and restricted
  credentials.
- Do not enable Flask debug mode in production.
- Run schema migrations manually through a reviewed database process; the
  application never runs destructive SQL at startup.

## Pre-deployment checklist

1. Back up the database.
2. Review and manually apply the Phase 6 migration.
3. Resolve duplicates and review the Phase 7 constraints migration.
4. Configure durable private document storage.
5. Set production environment variables in the hosting platform.
6. Verify `/health` without exposing configuration.
7. Run the unittest suite and a safe staging workflow.
