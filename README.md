# Conference Review Management System

A modern web-based Conference Review Management System developed using Flask and MySQL. The platform allows authors to submit research papers, reviewers to evaluate submissions, and administrators to manage the entire review workflow.

---

## Features

- User Registration & Login
- Submit Research Papers
- Manage Reviewers
- Assign Papers to Reviewers
- Submit Paper Reviews
- Review Dashboard
- Conference Analytics
- Secure Authentication
- Responsive User Interface

---

## Tech Stack

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- Flask

### Database
- MySQL

### Tools
- VS Code
- Git
- GitHub
- MySQL Workbench

---

## Folder Structure

conference_review/

├── app.py

├── requirements.txt

├── README.md

├── .env.example

├── database/

├── templates/

├── static/

├── screenshots/

---

## Installation

1. Clone the repository

```bash
git clone https://github.com/yourusername/conference-review-system.git
```

2. Move into the project

```bash
cd conference-review-system
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Configure the environment variables

Create a `.env` file using `.env.example`.

The `.env` file is local-only and must never be committed. Set the Flask
secret key and MySQL connection values before starting the application.

5. Start the server

```bash
python app.py
```

## Configuration

The application reads its Flask and MySQL settings from environment
variables. The repository includes [.env.example](.env.example) as a
template; copy it to `.env` and replace the placeholder values.

Never place real passwords, secret keys, or other credentials in tracked
Python, SQL, or documentation files.

Open:

http://127.0.0.1:5000

---

## Screenshots

Add screenshots inside the `screenshots` folder.

- Home Page
- Login
- Register
- Submit Paper
- Reviewer Dashboard

---

## Future Improvements

- Email Notifications
- PDF Upload
- AI-based Reviewer Recommendation
- Conference Statistics Dashboard

---

## Author

**Sakshi Shewale**

B.Tech Computer Science Engineering

MIT Academy of Engineering
