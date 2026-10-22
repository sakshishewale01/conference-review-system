# ConferenceFlow Phase 1: Flask Application Foundation

This document explains the foundation of ConferenceFlow in beginner-friendly
language. It focuses on the existing Flask application and the small
foundation changes made in Phase 1.

## 1. What Flask is

Flask is a Python web framework. A framework provides reusable tools and
conventions so we can build a web application without implementing an HTTP
server from scratch.

ConferenceFlow uses Flask to:

- receive requests from a browser;
- decide which Python function should handle each request;
- render HTML templates;
- return JSON for API-style endpoints; and
- send redirects when a user should visit another page.

The current Flask entry point is [app.py](../app.py).

## 2. What a web server does

A web server listens for HTTP requests. When the browser requests
`http://127.0.0.1:5000/`, the Flask development server receives that request,
finds the matching route, runs its Python function, and sends the function's
response back to the browser.

The server does not automatically know how ConferenceFlow works. The route
definitions in `app.py` teach Flask which code to run for each URL.

## 3. What a route is

A route connects a URL path and an HTTP method to a Python function:

```python
@app.route("/")
def home():
    return render_template("index.html")
```

The `@app.route("/")` line is a decorator. It registers `home()` as the
handler for a `GET` request to `/`.

The browser uses `GET` when it wants to retrieve a page. For example, opening
the home page sends a `GET /` request.

The health route is another simple example:

```python
@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        status="ok",
        service="ConferenceFlow"
    ), 200
```

This route returns a small JSON response rather than an HTML page. It is
useful for checking whether the Flask process is running.

## 4. GET and POST requests

`GET` normally retrieves information without changing data. Examples in this
project include:

- `GET /` to display the home page;
- `GET /login` to display the login form;
- `GET /papers` to display stored papers.

`POST` sends form data to the server, usually to create or change something.
The registration route supports both methods:

```python
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"]
        # Save the registration after validation.

    return render_template("auth/register.html")
```

On `GET`, Flask displays the form. On `POST`, Flask reads submitted values
from `request.form` and performs the registration operation.

## 5. HTTP status codes

An HTTP response includes a status code:

- `200 OK`: the request succeeded. The home page and health check use this
  when they work correctly.
- `404 Not Found`: the requested URL does not exist. Flask returns this for
  an unknown route.
- `500 Internal Server Error`: the server encountered an unexpected problem.
  ConferenceFlow returns a generic message for this case instead of exposing
  internal details to ordinary users.

The `500` handler in `app.py` logs the error on the server and returns:

```json
{
  "error": "Internal server error"
}
```

The response intentionally does not contain a traceback, password, secret
key, or database configuration.

## 6. Important Flask objects and functions

### `request`

`request` represents the incoming browser request. ConferenceFlow uses it to
read:

- the HTTP method with `request.method`;
- submitted form fields with `request.form`;
- uploaded files with `request.files`.

### `jsonify`

`jsonify` creates a JSON response with the correct content type. The
`/health` route uses it so monitoring tools can read a predictable response.

### `render_template`

`render_template("index.html")` loads an HTML file from the `templates`
folder and sends it to the browser. Jinja expressions such as
`{{ paper.title }}` are evaluated while the response is created.

### `redirect`

`redirect` tells the browser to visit another URL. For example, after a
successful login, the application redirects the user to the appropriate
dashboard instead of displaying the form again.

### `url_for`

`url_for("login")` builds a URL from a Flask endpoint function name. This is
safer than duplicating URL strings throughout the application because a route
can later change in one place.

## 7. Frontend, backend, and database

### Frontend

The frontend is what the user sees and interacts with in the browser:

- HTML templates in [templates/](../templates/)
- CSS in [static/css/style.css](../static/css/style.css)
- images and uploaded files in [static/](../static/)

### Backend

The backend runs on the server. In ConferenceFlow, Flask code in
[app.py](../app.py) receives requests, validates input, calls the database,
and chooses a response.

### Database

The MySQL database stores information after the server finishes its
validation. The connection helper is [db.py](../db.py), and the table
definitions are in [schema.sql](../schema.sql).

The browser should not connect directly to MySQL. The backend acts as a
controlled middle layer between the browser and the database.

## 8. How a browser request travels through Flask

For a home-page request:

1. The browser sends `GET /`.
2. Flask matches `/` to `home()`.
3. `home()` calls `render_template("index.html")`.
4. Jinja loads the base layout and page content.
5. The browser receives HTML.
6. The browser requests the CSS referenced by the HTML.
7. Flask's static-file handling sends `static/css/style.css`.
8. The browser applies the CSS and displays the page.

For a form submission:

1. The browser sends a `POST` request with form data.
2. Flask makes that data available through `request.form`.
3. The route validates and processes the values.
4. The route may use `db.get_connection()` to communicate with MySQL.
5. The route commonly redirects after a successful change.

## 9. Templates and the static folder

Flask looks for HTML templates in `templates/`. The shared layout is
[templates/base.html](../templates/base.html). Page templates use
`{% extends "base.html" %}` so navigation and common styling do not need to
be copied into every file.

The `static/` folder contains files that are served directly, such as CSS.
The base template loads the stylesheet with:

```html
{{ url_for('static', filename='css/style.css') }}
```

`url_for` generates the correct static URL.

## 10. Environment variables and `.gitignore`

Configuration that changes between computers should not be hardcoded in
source code. ConferenceFlow reads the Flask secret key and MySQL settings
from environment variables. `.env.example` documents the required names
without containing real credentials.

Create a local `.env` file from the example and replace its placeholders.
The `.gitignore` file contains `.env`, so Git will not include that local
secret file in commits.

Never commit real passwords or secret keys. The `.env.example` file is safe
to share because it contains placeholders only.

## 11. Files involved in Phase 1

| File | Purpose |
| --- | --- |
| [app.py](../app.py) | Flask application, routes, templates, health check, and error handling |
| [db.py](../db.py) | Reads database configuration and creates MySQL connections when a route needs one |
| [requirements.txt](../requirements.txt) | Lists Python packages needed by the application |
| [.env.example](../.env.example) | Documents required local configuration names |
| [.gitignore](../.gitignore) | Prevents local secrets and generated files from being committed |
| [templates/](../templates/) | HTML templates rendered by Flask |
| [static/](../static/) | CSS and other directly served assets |
| [schema.sql](../schema.sql) | MySQL database and table definitions |

## 12. Common errors and troubleshooting

### `FLASK_SECRET_KEY is required`

Copy `.env.example` to `.env` and set a local secret key. On Windows
PowerShell, you can create a value with:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and replace the placeholder.

### `ModuleNotFoundError`

The active Python interpreter may not have the dependencies installed. Use
the existing project requirements file:

```powershell
python -m pip install -r requirements.txt
```

Do not install packages into the project blindly; first verify which
interpreter VS Code is using.

### MySQL connection errors

The home page and `/health` route do not need an active database connection.
Database-backed routes such as registration and paper listing do. Check that
MySQL is running and that the four `MYSQL_*` values in `.env` are correct.
Never paste the password into a public issue or chat.

### `404 Not Found`

Check the URL spelling and confirm that a matching `@app.route()` exists.
For example, `/health` and `/health/` are different paths unless both are
registered.

### CSS does not load

Confirm that the file exists at `static/css/style.css` and that the template
uses `url_for('static', filename='css/style.css')`. Also inspect the browser
developer tools Network tab for the CSS request status.

### A page shows a server error

Look at the Flask terminal output for the server-side log. In production,
users receive a generic error response rather than a traceback. During local
development, use controlled logging and tests rather than exposing debug
mode on a deployed server.
