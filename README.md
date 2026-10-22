
# ConferenceFlow

ConferenceFlow is a Flask and MySQL web application that streamlines academic conference workflows—from paper submission and reviewer assignment to structured peer review, editorial decisions, and notifications.

## Key Features

- **Author Portal** — Submit PDF papers, track submission status, and view released decisions.
- **Reviewer Portal** — Access assigned papers, submit structured evaluations, and track review progress.
- **Admin Dashboard** — Assign reviewers, monitor review activity, and publish official acceptance or rejection decisions.
- **Workflow Management** — Track submissions, reviews, decisions, and notifications through a centralized system.
- **Security** — Password hashing, server-side role checks, CSRF protection, parameterized SQL queries, and authorization-controlled paper access.
- **Testing** — Automated regression and security tests using Python `unittest`.

## Workflow

<escape>Author Submission → Reviewer Assignment → Peer Review → Editorial Decision → Author Notification</escape>

Reviewer recommendations inform the editorial process; the administrator makes the official decision.

## Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python, Flask |
| Database | MySQL |
| Frontend | HTML, CSS, JavaScript, Jinja2 |
| Testing | Python `unittest` |
| Deployment Configuration | Vercel |

## Project Structure

```text
conference-review-system/
├── app.py                 # Application routes and workflows
├── db.py                  # Database connections and transactions
├── schema.sql             # Database schema
├── database/              # SQL migration proposals
├── templates/             # Jinja2 templates
├── static/                # CSS, JavaScript, and assets
├── instance/uploads/      # Local PDF storage
├── tests/                 # Automated tests
├── docs/                  # Setup and deployment documentation
├── api/index.py           # Vercel entry point
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
└── vercel.json            # Deployment routing
```

## Getting Started

### Prerequisites

- Python 3.10 or compatible version required by the installed dependencies
- MySQL Server
- Git

### 1. Clone the repository

```powershell
git clone https://github.com/sakshishewale01/conference-review-system.git
cd conference-review-system
```

### 2. Set up the environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3. Configure MySQL

Create a development database and configure the required values in `.env`.

```powershell
Copy-Item .env.example .env
```

Configure the MySQL host, port, username, password, database name, and Flask secret key. Apply `schema.sql` only to a fresh development database; review migration scripts before using them with an existing database.

**Never commit `.env` or expose production credentials.**

### 4. Run the application

```powershell
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

Health check: `http://127.0.0.1:5000/health`

## Testing

Run the automated test suite:

```powershell
python -m unittest discover -s tests -v
```

Check Python syntax:

```powershell
python -m py_compile app.py db.py api/index.py
```

Check the Git diff for whitespace errors:

```powershell
git diff --check
```

The automated tests include mocked database tests. Live MySQL integration and end-to-end testing must be performed separately.

## Author

**Sakshi Shewale**  
B.Tech, Computer Science and Engineering  
MIT Academy of Engineering

[GitHub Repository](https://github.com/sakshishewale01/conference-review-system)

