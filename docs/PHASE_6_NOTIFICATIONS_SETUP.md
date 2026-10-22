# Phase 6 Notifications Setup

## Migration status

The application includes an unapplied proposal at
`database/phase6_decisions_notifications.sql`. It adds paper ownership,
decision metadata, and a recipient-owned notification table. Do not run it
against production without a backup, a reviewed ownership backfill, and an
approved rollback plan.

## Windows PowerShell checks

```powershell
Get-Service *MySQL*
mysql --version
mysql -u <local-user> -p
```

Inspect the local schema before applying anything:

```sql
USE conf_review_system;
SHOW COLUMNS FROM papers;
SHOW TABLES;
```

Apply the proposal only to a fresh backup of a local development database and
inspect the commented statements before executing them. Never paste a real
password into a script or commit `.env`.

## Run and test

```powershell
python -m unittest discover -s .\tests -p "test_*.py" -v
python app.py
```

The application uses normal page requests rather than polling or browser push
notifications. Each notification has one recipient, an application-generated
link, an unread state, and a unique event key to reduce duplicates.

## Troubleshooting

- A missing `notifications` table means the reviewed local migration has not
  been applied.
- Existing papers with a null owner require a manual, evidence-based backfill.
- MySQL connection errors should be investigated using the non-secret host,
  port, database, and user settings; never print the password.
- A failed decision or notification write should return a generic error and
  leave the transaction rolled back.
