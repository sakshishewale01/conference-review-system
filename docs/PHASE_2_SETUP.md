# ConferenceFlow Phase 2: Windows MySQL Setup

These instructions are for a local development database only. They do not
apply schema changes to production and do not delete existing data.

## 1. Check MySQL installation and service status

In PowerShell, check whether the MySQL client is available:

```powershell
mysql --version
```

Check Windows services for a MySQL service:

```powershell
Get-Service | Where-Object {
    $_.Name -match "mysql" -or $_.DisplayName -match "mysql"
}
```

If the service is installed but stopped, start it using the exact service
name shown by the previous command:

```powershell
Start-Service -Name "MySQL80"
```

Do not guess a service name if your installation uses a different one.

## 2. Configure local environment variables

From the repository root:

```powershell
Copy-Item .env.example .env
```

Open `.env` in VS Code and set local values for:

- `FLASK_SECRET_KEY`
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

The `.env` file is ignored by Git. Never paste its contents into a commit,
issue, screenshot, or public chat.

## 3. Create a fresh local development database

Only run this against a database name that you have confirmed is a fresh
local development database. This command does not drop or truncate anything:

```powershell
mysql -u root -p
```

At the MySQL prompt, create the database if it does not already exist:

```sql
CREATE DATABASE IF NOT EXISTS conf_review_system;
EXIT;
```

The `-p` option prompts for the password without placing it in the command
history.

## 4. Apply the schema to a fresh database

The current [schema.sql](../schema.sql) includes `CREATE DATABASE` and
`USE` statements. Apply it only to a fresh local development database after
confirming that you are not targeting production:

```powershell
Get-Content .\schema.sql | mysql -u root -p
```

Do not run this command against an existing database without first reviewing
the schema and checking its data. Phase 2 does not apply migrations
automatically, and no destructive SQL should be added to this process.

## 5. Verify tables and relationships

Connect to the local database:

```powershell
mysql -u root -p conf_review_system
```

Run read-only verification queries:

```sql
SHOW TABLES;
DESCRIBE users;
DESCRIBE papers;
DESCRIBE review_assignments;
DESCRIBE reviews;
SHOW CREATE TABLE review_assignments;
SHOW CREATE TABLE reviews;
SHOW INDEX FROM users;
EXIT;
```

`SHOW CREATE TABLE` should show the foreign keys from assignments to papers
and users, and from reviews to assignments. `SHOW INDEX` should show the
unique index created for `users.email`.

## 6. Verify Flask without requiring MySQL

The home page and health check do not call `get_connection()`. After setting
`FLASK_SECRET_KEY` in `.env`, run:

```powershell
python -m py_compile .\app.py .\db.py
python .\app.py
```

In another PowerShell window:

```powershell
Invoke-WebRequest http://127.0.0.1:5000/health
Invoke-WebRequest http://127.0.0.1:5000/
```

Stop the development server with `Ctrl+C`.

Database-backed routes such as `/login`, `/register`, `/papers`, and
`/assign` require a working local MySQL connection and valid local data.

## 7. Troubleshooting

### `mysql is not recognized`

MySQL's `bin` directory may not be on `PATH`. Use the MySQL Workbench SQL
editor, or add the installed MySQL `bin` directory to PATH through Windows
environment settings. Restart the terminal after changing PATH.

### `Can't connect to MySQL server`

Check that the MySQL Windows service is running and that `MYSQL_HOST` and
`MYSQL_PORT` match the local installation.

### `Access denied for user`

Check the local username and password in `.env`. Do not put the password in a
PowerShell command or commit it to a file. If the password is unknown, reset
the local development account through an approved local MySQL
administration process.

### `Unknown database`

Create the local database using the `CREATE DATABASE IF NOT EXISTS` command
above, then apply the schema to that database.

### Missing Python package

Use the repository's dependency file:

```powershell
python -m pip install -r .\requirements.txt
```

Do not change package versions silently. Record any approved dependency
change separately.

## 9. Run the isolated database-layer tests

These tests use mocks and do not connect to MySQL or modify data:

```powershell
python -m unittest discover -s .\tests -p "test_*.py" -v
```

MySQL integration tests require a confirmed local development database. Do
not point tests at production or an unknown existing database.

## 8. Data-safety checklist

Before running any SQL:

1. Confirm the MySQL host is local.
2. Confirm the database name is a development database.
3. Do not run `DROP`, `TRUNCATE`, or unreviewed `DELETE` statements.
4. Do not apply proposed schema constraints until existing data has been
   checked and the migration has been approved.
5. Keep backups of important data before approved migrations.
