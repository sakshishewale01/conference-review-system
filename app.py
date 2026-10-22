from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    abort,
    send_file
)

from db import cursor_scope

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename

import os
import re
import secrets
from functools import wraps
from email.utils import parseaddr

from mysql.connector import Error as MySQLError
from dotenv import load_dotenv

load_dotenv()



# =====================================================
# APP CONFIGURATION
# =====================================================

app = Flask(__name__)

secret_key = os.getenv("FLASK_SECRET_KEY")
if not secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY is required. Copy .env.example to .env and set it."
    )

app.secret_key = secret_key

UPLOAD_FOLDER = os.path.join(app.instance_path, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("FLASK_ENV", "development").lower() == "production"
)
app.config["PERMANENT_SESSION_LIFETIME"] = 3600
app.config["ALLOWED_UPLOAD_EXTENSIONS"] = {"pdf"}
app.config["MAX_NAME_LENGTH"] = 150
app.config["MAX_EMAIL_LENGTH"] = 150
app.config["MIN_PASSWORD_LENGTH"] = 12
app.config["MAX_TITLE_LENGTH"] = 255
app.config["MAX_ABSTRACT_LENGTH"] = 10000
app.config["MAX_KEYWORDS_LENGTH"] = 1000
app.config["MIN_TITLE_LENGTH"] = 5
app.config["MIN_ABSTRACT_LENGTH"] = 50
app.config["PAPER_STATUSES"] = {
    "Pending",
    "Under Review",
    "Accepted",
    "Rejected",
}
app.config["DECISION_VALUES"] = {"Accepted", "Rejected"}
app.config["MAX_DECISION_NOTES_LENGTH"] = 5000


def _csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def _validate_csrf():
    expected = session.get("_csrf_token")
    submitted = request.form.get("_csrf_token") or request.headers.get(
        "X-CSRF-Token"
    )
    if not expected or not submitted or not secrets.compare_digest(
        expected, submitted
    ):
        abort(400, description="Invalid CSRF token")


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": _csrf_token}


@app.context_processor
def inject_notification_count():
    user_id = session.get("user_id")
    unread_count = 0
    user_role = None
    if user_id:
        try:
            with cursor_scope(dictionary=True) as (conn, cur):
                cur.execute(
                    "SELECT role FROM users WHERE user_id=%s",
                    (user_id,),
                )
                user = cur.fetchone()
                user_role = user["role"] if user else None
                cur.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM notifications
                    WHERE recipient_id=%s AND read_at IS NULL
                    """,
                    (user_id,),
                )
                unread_count = cur.fetchone()["total"]
        except (MySQLError, RuntimeError):
            app.logger.warning("Notification count unavailable")
    return {
        "unread_notification_count": unread_count,
        "current_user_role": user_role,
    }


@app.before_request
def protect_state_changing_requests():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        _validate_csrf()


def _current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    with cursor_scope(dictionary=True) as (conn, cur):
        cur.execute(
            """
            SELECT user_id, full_name, email, role
            FROM users
            WHERE user_id=%s
            """,
            (user_id,),
        )
        return cur.fetchone()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            user = _current_user()
        except (MySQLError, RuntimeError):
            return jsonify(error="Authentication temporarily unavailable"), 503
        if not user:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def role_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            try:
                user = _current_user()
            except (MySQLError, RuntimeError):
                return jsonify(error="Authorization temporarily unavailable"), 503
            if not user:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if user["role"] not in allowed_roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def _clean_text(value, field_name, max_length):
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{field_name} is required.")
    if len(value) > max_length:
        raise ValueError(f"{field_name} is too long.")
    return value


def _create_notification(cursor, recipient_id, title, message, link, event_key):
    cursor.execute(
        """
        INSERT INTO notifications
        (recipient_id, title, message, link, event_key)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE notification_id=notification_id
        """,
        (recipient_id, title, message, link, event_key),
    )


def _clean_email(value):
    email = (value or "").strip().lower()
    parsed_name, parsed_email = parseaddr(email)
    if (
        parsed_name
        or parsed_email != email
        or len(email) > app.config["MAX_EMAIL_LENGTH"]
        or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
    ):
        raise ValueError("Enter a valid email address.")
    return email


def _safe_next_url(value):
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return url_for("author_dashboard")


def _allowed_upload(filename):
    return (
        bool(filename)
        and "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in app.config["ALLOWED_UPLOAD_EXTENSIONS"]
    )


def _paper_access_allowed(cursor, paper_id, user):
    if user["role"] == "admin":
        return True
    if user["role"] == "author":
        cursor.execute(
            "SELECT 1 FROM papers WHERE paper_id=%s AND author_id=%s",
            (paper_id, user["user_id"]),
        )
        return cursor.fetchone() is not None
    if user["role"] != "reviewer":
        return False
    cursor.execute(
        """
        SELECT 1
        FROM review_assignments
        WHERE paper_id=%s AND reviewer_id=%s
        """,
        (paper_id, user["user_id"]),
    )
    return cursor.fetchone() is not None


# =====================================================
# HEALTH CHECK
# =====================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        status="ok",
        service="ConferenceFlow"
    ), 200


# =====================================================
# ERROR HANDLING
# =====================================================

@app.errorhandler(500)
def internal_server_error(error):
    app.logger.error(
        "Unhandled application error: %s",
        type(error).__name__
    )
    return jsonify(
        error="Internal server error"
    ), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify(error="Bad request"), 400


@app.errorhandler(403)
def forbidden(error):
    return jsonify(error="Forbidden"), 403


@app.errorhandler(404)
def not_found(error):
    return jsonify(error="Not found"), 404


@app.errorhandler(413)
def request_too_large(error):
    return jsonify(error="Uploaded file is too large"), 413



# =====================================================
# HOME PAGE
# =====================================================

@app.route("/")
def home():
    return render_template("index.html")



# =====================================================
# REGISTER
# =====================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        try:
            full_name = _clean_text(
                request.form.get("full_name"),
                "Full name",
                app.config["MAX_NAME_LENGTH"],
            )
            email = _clean_email(request.form.get("email"))
            password = request.form.get("password", "")
            if len(password) < app.config["MIN_PASSWORD_LENGTH"]:
                raise ValueError(
                    "Password must be at least 12 characters long."
                )
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("auth/register.html"), 400

        hashed_password = generate_password_hash(password)

        try:
            with cursor_scope() as (conn, cur):
                cur.execute("""
                    SELECT * FROM users
                    WHERE email=%s
                """, (email,))

                existing_user = cur.fetchone()

                if existing_user:
                    flash(
                        "Unable to create account with those details.",
                        "warning"
                    )
                    return redirect(url_for("register"))

                cur.execute("""
                    INSERT INTO users
                    (
                        full_name,
                        email,
                        password,
                        role
                    )
                    VALUES (%s, %s, %s, %s)
                """, (
                    full_name,
                    email,
                    hashed_password,
                    "author"
                ))
                conn.commit()
        except (MySQLError, RuntimeError) as error:
            app.logger.error(
                "Registration database operation failed: %s",
                type(error).__name__
            )
            flash(
                "Registration is temporarily unavailable. Please try again.",
                "danger"
            )
            return render_template("auth/register.html"), 503

        flash(
            "Registration successful!",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("auth/register.html")



# =====================================================
# LOGIN
# =====================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        try:
            email = _clean_email(request.form.get("email"))
            password = request.form.get("password", "")
            if not password:
                raise ValueError("Email and password are required.")
        except ValueError:
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html"), 400

        try:
            with cursor_scope(dictionary=True) as (conn, cur):
                cur.execute("""
                    SELECT * FROM users
                    WHERE email=%s
                """, (email,))
                user = cur.fetchone()
        except (MySQLError, RuntimeError) as error:
            app.logger.error(
                "Login database operation failed: %s",
                type(error).__name__
            )
            flash(
                "Login is temporarily unavailable. Please try again.",
                "danger"
            )
            return render_template("auth/login.html"), 503

        if user and check_password_hash(
            user["password"],
            password
        ):
            target = _safe_next_url(request.args.get("next"))
            session.clear()
            session["user_id"] = user["user_id"]
            session.permanent = True

            flash(
                "Login successful!",
                "success"
            )

            # ROLE BASED DASHBOARD
            if user["role"] == "admin":
                target = url_for("admin_dashboard")

            elif user["role"] == "reviewer":
                target = url_for("reviewer_dashboard")

            else:
                target = target or url_for("author_dashboard")

            return redirect(target)

        else:

            flash(
                "Invalid email or password.",
                "danger"
            )

    return render_template("auth/login.html")



# =====================================================
# LOGOUT
# =====================================================

@app.route("/logout", methods=["POST"])
@login_required
def logout():

    session.clear()

    flash(
        "Logged out successfully!",
        "info"
    )

    return redirect(url_for("login"))



# =====================================================
# ADMIN DASHBOARD
# =====================================================

@app.route("/admin_dashboard")
@role_required("admin")
def admin_dashboard():
    try:
        with cursor_scope(dictionary=True) as (conn, cur):
            cur.execute("""
                SELECT COUNT(*) AS total
                FROM papers
            """)
            total_papers = cur.fetchone()["total"]

            cur.execute("""
                SELECT COUNT(*) AS total
                FROM papers
                WHERE status='Accepted'
            """)
            accepted_papers = cur.fetchone()["total"]

            cur.execute("""
                SELECT COUNT(*) AS total
                FROM papers
                WHERE status='Rejected'
            """)
            rejected_papers = cur.fetchone()["total"]

            cur.execute("""
                SELECT COUNT(*) AS total
                FROM users
                WHERE role='reviewer'
            """)
            total_reviewers = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) AS total FROM review_assignments")
            total_assignments = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) AS total FROM reviews")
            completed_reviews = cur.fetchone()["total"]

            cur.execute("""
                SELECT COUNT(*) AS total
                FROM papers AS p
                WHERE NOT EXISTS (
                    SELECT 1 FROM review_assignments AS ra
                    WHERE ra.paper_id=p.paper_id
                )
            """)
            papers_awaiting_assignment = cur.fetchone()["total"]

            cur.execute("""
                SELECT COUNT(*) AS total
                FROM review_assignments AS ra
                LEFT JOIN reviews AS r ON r.assignment_id = ra.assignment_id
                WHERE r.review_id IS NULL
            """)
            pending_reviews = cur.fetchone()["total"]

            cur.execute("""
                SELECT COUNT(*) AS total
                FROM papers AS p
                WHERE p.status NOT IN ('Accepted', 'Rejected')
                AND EXISTS (
                    SELECT 1 FROM review_assignments AS ra
                    WHERE ra.paper_id=p.paper_id
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM review_assignments AS ra
                    LEFT JOIN reviews AS r ON r.assignment_id=ra.assignment_id
                    WHERE ra.paper_id=p.paper_id AND r.review_id IS NULL
                )
            """)
            papers_awaiting_decision = cur.fetchone()["total"]
    except (MySQLError, RuntimeError) as error:
        app.logger.error(
            "Dashboard database operation failed: %s",
            type(error).__name__
        )
        return jsonify(error="Database temporarily unavailable"), 503

    return render_template(
        "dashboard/admin_dashboard.html",
        total_papers=total_papers,
        accepted_papers=accepted_papers,
        rejected_papers=rejected_papers,
        total_reviewers=total_reviewers,
        total_assignments=total_assignments,
        completed_reviews=completed_reviews,
        pending_reviews=pending_reviews,
        papers_awaiting_assignment=papers_awaiting_assignment,
        papers_awaiting_decision=papers_awaiting_decision,
    )



# =====================================================
# REVIEWER DASHBOARD
# =====================================================

@app.route("/reviewer_dashboard")
@role_required("reviewer")
def reviewer_dashboard():
    try:
        with cursor_scope(dictionary=True) as (conn, cur):
            cur.execute("""
                SELECT ra.assignment_id, ra.paper_id, p.title, p.status,
                       p.submitted_at,
                       CASE WHEN r.review_id IS NULL
                            THEN 'Pending' ELSE 'Completed' END AS review_status
                FROM review_assignments AS ra
                JOIN papers AS p ON p.paper_id = ra.paper_id
                LEFT JOIN reviews AS r ON r.assignment_id = ra.assignment_id
                WHERE ra.reviewer_id=%s
                ORDER BY ra.assigned_at DESC
                LIMIT 100
            """, (session["user_id"],))
            assignments = cur.fetchall()
    except (MySQLError, RuntimeError) as error:
        app.logger.error(
            "Reviewer dashboard database operation failed: %s",
            type(error).__name__
        )
        return jsonify(error="Database temporarily unavailable"), 503

    completed_reviews = sum(
        assignment["review_status"] == "Completed"
        for assignment in assignments
    )
    return render_template(
        "dashboard/reviewer_dashboard.html",
        assignments=assignments,
        total_assignments=len(assignments),
        completed_reviews=completed_reviews,
        pending_reviews=len(assignments) - completed_reviews,
    )



# =====================================================
# AUTHOR DASHBOARD
# =====================================================

@app.route("/author_dashboard")
@role_required("author")
def author_dashboard():
    try:
        with cursor_scope(dictionary=True) as (conn, cur):
            cur.execute("""
                SELECT COUNT(*) AS total,
                       SUM(status='Accepted') AS accepted,
                       SUM(status='Rejected') AS rejected
                FROM papers
                WHERE author_id=%s
            """, (session["user_id"],))
            counts = cur.fetchone()
            cur.execute("""
                SELECT paper_id, title, status, submitted_at,
                       decision_released_at
                FROM papers
                WHERE author_id=%s
                ORDER BY submitted_at DESC
                LIMIT 100
            """, (session["user_id"],))
            papers = cur.fetchall()
    except (MySQLError, RuntimeError) as error:
        app.logger.error(
            "Author dashboard database operation failed: %s",
            type(error).__name__
        )
        return jsonify(error="Dashboard temporarily unavailable"), 503
    return render_template(
        "dashboard/author_dashboard.html",
        total_papers=counts["total"] or 0,
        accepted_papers=counts["accepted"] or 0,
        rejected_papers=counts["rejected"] or 0,
        papers=papers,
    )



# =====================================================
# SUBMIT PAPER
# =====================================================

@app.route(
    "/submit_paper",
    methods=["GET", "POST"]
)
@role_required("author", "admin")
def submit_paper():
    user = _current_user()

    if request.method == "POST":
        try:
            title = _clean_text(
                request.form.get("title"),
                "Title",
                app.config["MAX_TITLE_LENGTH"],
            )
            if len(title) < app.config["MIN_TITLE_LENGTH"]:
                raise ValueError("Title is too short.")
            abstract = _clean_text(
                request.form.get("abstract"),
                "Abstract",
                app.config["MAX_ABSTRACT_LENGTH"],
            )
            if len(abstract) < app.config["MIN_ABSTRACT_LENGTH"]:
                raise ValueError("Abstract is too short.")
            keywords = _clean_text(
                request.form.get("keywords"),
                "Keywords",
                app.config["MAX_KEYWORDS_LENGTH"],
            )
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("papers/submit_paper.html"), 400

        paper_file = request.files.get("paper_file")
        filename = secure_filename(paper_file.filename if paper_file else "")
        if not paper_file or not filename or not _allowed_upload(filename):
            flash("Please upload a PDF file.", "danger")
            return render_template("papers/submit_paper.html"), 400

        stored_filename = f"{secrets.token_hex(16)}.pdf"
        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            stored_filename
        )
        paper_file.save(filepath)

        try:
            with cursor_scope() as (conn, cur):
                cur.execute("""
                    INSERT INTO papers
                    (
                            author_id,
                            title,
                        abstract,
                        keywords,
                        file_name,
                        uploaded_file_path,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    user["user_id"],
                    title,
                    abstract,
                    keywords,
                    filename,
                    filepath,
                    "Pending"
                ))
                paper_id = cur.lastrowid
                cur.execute(
                    """
                    INSERT INTO notifications
                    (recipient_id, title, message, link, event_key)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        user["user_id"],
                        "Paper submitted",
                        "Your paper was submitted successfully.",
                        url_for("papers"),
                        f"paper-submitted:{paper_id}",
                    ),
                )
                conn.commit()
        except (MySQLError, RuntimeError) as error:
            if os.path.exists(filepath):
                os.remove(filepath)
            app.logger.error(
                "Paper submission database operation failed: %s",
                type(error).__name__
            )
            flash(
                "Paper submission is temporarily unavailable. Please try again.",
                "danger"
            )
            return render_template("papers/submit_paper.html"), 503

        flash(
            "Paper submitted successfully!",
            "success"
        )

        return redirect(url_for("papers"))

    return render_template(
        "papers/submit_paper.html"
    )



# =====================================================
# VIEW PAPERS
# =====================================================

@app.route("/papers")
@login_required
def papers():
    user = _current_user()
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    if status and status not in app.config["PAPER_STATUSES"]:
        abort(400)
    if len(search) > 100:
        abort(400)

    try:
        with cursor_scope(dictionary=True) as (conn, cur):
            query = """
                SELECT *
                FROM papers
                WHERE 1=1
            """
            values = []
            if search:
                query += " AND (title LIKE %s OR paper_id = %s)"
                values.extend([f"%{search}%", search if search.isdigit() else -1])
            if status:
                query += " AND status=%s"
                values.append(status)
            if user["role"] == "reviewer":
                query += """
                    AND paper_id IN (
                        SELECT paper_id
                        FROM review_assignments
                        WHERE reviewer_id=%s
                    )
                """
                values.append(user["user_id"])
            elif user["role"] == "author":
                query += " AND author_id=%s"
                values.append(user["user_id"])
            query += " ORDER BY submitted_at DESC LIMIT 100"
            cur.execute(query, tuple(values))
            papers = cur.fetchall()
    except (MySQLError, RuntimeError) as error:
        app.logger.error(
            "Paper listing database operation failed: %s",
            type(error).__name__
        )
        return jsonify(error="Database temporarily unavailable"), 503

    return render_template(
        "papers/papers.html",
        papers=papers,
        search=search,
        selected_status=status,
        statuses=sorted(app.config["PAPER_STATUSES"]),
    )


@app.route("/papers/<int:paper_id>")
@login_required
def paper_details(paper_id):
    user = _current_user()
    try:
        with cursor_scope(dictionary=True) as (conn, cur):
            cur.execute(
                "SELECT * FROM papers WHERE paper_id=%s",
                (paper_id,),
            )
            paper = cur.fetchone()
            if not paper or not _paper_access_allowed(cur, paper_id, user):
                abort(404)
    except (MySQLError, RuntimeError):
        return jsonify(error="Paper temporarily unavailable"), 503

    return render_template("papers/paper_details.html", paper=paper)



# =====================================================
# REVIEWERS
# =====================================================

@app.route("/reviewers")
@role_required("admin")
def reviewers():
    try:
        with cursor_scope(dictionary=True) as (conn, cur):
            cur.execute("""
                SELECT *
                FROM users
                WHERE role='reviewer'
            """)
            reviewers = cur.fetchall()
    except (MySQLError, RuntimeError) as error:
        app.logger.error(
            "Reviewer listing database operation failed: %s",
            type(error).__name__
        )
        return jsonify(error="Database temporarily unavailable"), 503

    return render_template(
        "reviewers/reviewers.html",
        reviewers=reviewers
    )



# =====================================================
# ASSIGN REVIEWER
# =====================================================

@app.route("/assign", methods=["GET", "POST"])
@role_required("admin")
def assign():
    if request.method == "POST":
        try:
            paper_id = int(request.form["paper_id"])
            reviewer_id = int(request.form["reviewer_id"])
        except (KeyError, TypeError, ValueError):
            flash("Select a valid paper and reviewer.", "danger")
            return redirect(url_for("assign"))

        try:
            with cursor_scope(dictionary=True) as (conn, cur):
                cur.execute(
                    "SELECT paper_id FROM papers WHERE paper_id=%s",
                    (paper_id,),
                )
                if not cur.fetchone():
                    flash("The selected paper does not exist.", "danger")
                    return redirect(url_for("assign"))

                cur.execute(
                    """
                    SELECT user_id FROM users
                    WHERE user_id=%s AND role='reviewer'
                    """,
                    (reviewer_id,),
                )
                if not cur.fetchone():
                    flash("The selected account is not a reviewer.", "danger")
                    return redirect(url_for("assign"))

                cur.execute("""
                    SELECT *
                    FROM review_assignments
                    WHERE paper_id = %s
                    AND reviewer_id = %s
                """, (paper_id, reviewer_id))
                existing_assignment = cur.fetchone()

                if existing_assignment:
                    flash(
                        "Reviewer already assigned to this paper!",
                        "warning"
                    )
                else:
                    cur.execute("""
                        INSERT INTO review_assignments
                        (
                            paper_id,
                            reviewer_id
                        )
                        VALUES (%s, %s)
                    """, (paper_id, reviewer_id))
                    assignment_id = cur.lastrowid
                    cur.execute("""
                        UPDATE papers
                        SET status = 'Under Review'
                        WHERE paper_id = %s
                    """, (paper_id,))
                    _create_notification(
                        cur,
                        reviewer_id,
                        "New paper assignment",
                        "A paper has been assigned to you for review.",
                        url_for("review"),
                        f"assignment-created:{assignment_id}",
                    )
                    conn.commit()
                    flash(
                        "Reviewer assigned successfully!",
                        "success"
                    )
        except (MySQLError, RuntimeError) as error:
            app.logger.error(
                "Reviewer assignment database operation failed: %s",
                type(error).__name__
            )
            flash(
                "Reviewer assignment is temporarily unavailable. Please try again.",
                "danger"
            )

        return redirect(url_for("admin_dashboard"))

    try:
        with cursor_scope(dictionary=True) as (conn, cur):
            cur.execute("""
                SELECT *
                FROM papers
                ORDER BY submitted_at DESC
            """)
            papers = cur.fetchall()

            cur.execute("""
                SELECT *
                FROM users
                WHERE role = 'reviewer'
            """)
            reviewers = cur.fetchall()

            cur.execute("""
                SELECT ra.assignment_id, p.title, u.full_name,
                       CASE WHEN r.review_id IS NULL
                            THEN 'Pending' ELSE 'Completed' END AS review_status
                FROM review_assignments AS ra
                JOIN papers AS p ON p.paper_id = ra.paper_id
                JOIN users AS u ON u.user_id = ra.reviewer_id
                LEFT JOIN reviews AS r ON r.assignment_id = ra.assignment_id
                ORDER BY ra.assigned_at DESC
                LIMIT 100
            """)
            assignments = cur.fetchall()
    except (MySQLError, RuntimeError) as error:
        app.logger.error(
            "Assignment page database operation failed: %s",
            type(error).__name__
        )
        return jsonify(error="Database temporarily unavailable"), 503

    return render_template(
        "reviews/assign.html",
        papers=papers,
        reviewers=reviewers,
        assignments=assignments,
    )

# =====================================================
# SUBMIT REVIEW
# =====================================================

@app.route(
    "/review",
    methods=["GET", "POST"]
)
@role_required("reviewer")
def review():
    if request.method == "POST":
        try:
            assignment_id = int(request.form["assignment_id"])
            scores = [
                float(request.form[field])
                for field in (
                    "technical_merit",
                    "readability",
                    "originality",
                    "relevance",
                )
            ]
            if any(score < 1 or score > 10 for score in scores):
                raise ValueError
            (
                technical_merit,
                readability,
                originality,
                relevance,
            ) = scores
            recommendation = request.form["recommendation"]
            if recommendation not in {"Accepted", "Rejected", "Borderline"}:
                raise ValueError
            review_comment = _clean_text(
                request.form.get("review_comment"),
                "Review comments",
                10000,
            )
        except (KeyError, TypeError, ValueError):
            flash("Enter valid review details.", "danger")
            return render_template(
                "reviews/review.html",
                assignments=[],
            ), 400

        user_id = session["user_id"]

        overall_score = round(
            (
                technical_merit +
                readability +
                originality +
                relevance
            ) / 4,
            1
        )

        try:
            with cursor_scope(dictionary=True) as (conn, cur):
                cur.execute(
                    """
                    SELECT assignment_id
                    FROM review_assignments
                    WHERE assignment_id=%s AND reviewer_id=%s
                    """,
                    (assignment_id, user_id),
                )
                if not cur.fetchone():
                    abort(404)

                cur.execute(
                    "SELECT review_id FROM reviews WHERE assignment_id=%s",
                    (assignment_id,),
                )
                if cur.fetchone():
                    flash(
                        "This assignment already has a submitted review.",
                        "warning"
                    )
                    return redirect(url_for("review"))

                cur.execute("""
                    INSERT INTO reviews
                    (
                        assignment_id,
                        technical_merit,
                        readability,
                        originality,
                        relevance,
                        overall_score,
                        recommendation,
                        review_comment
                    )
                    VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    assignment_id,
                    technical_merit,
                    readability,
                    originality,
                    relevance,
                    overall_score,
                    recommendation,
                    review_comment
                ))
                cur.execute(
                    """
                    SELECT DISTINCT u.user_id
                    FROM users AS u
                    WHERE u.role='admin'
                    """
                )
                for administrator in cur.fetchall():
                    _create_notification(
                        cur,
                        administrator["user_id"],
                        "Review submitted",
                        "A reviewer has completed an assigned review.",
                        url_for("decision_list"),
                        f"review-submitted:{assignment_id}:{administrator['user_id']}",
                    )
                conn.commit()
        except (MySQLError, RuntimeError) as error:
            app.logger.error(
                "Review submission database operation failed: %s",
                type(error).__name__
            )
            flash(
                "Review submission is temporarily unavailable. Please try again.",
                "danger"
            )
            return render_template("reviews/review.html"), 503

        flash(
            "Review submitted successfully!",
            "success"
        )

        return redirect(
            url_for("reviewer_dashboard")
        )

    try:
        with cursor_scope(dictionary=True) as (conn, cur):
            cur.execute("""
                SELECT ra.assignment_id, ra.paper_id, p.title, p.status
                FROM review_assignments AS ra
                JOIN papers AS p ON p.paper_id = ra.paper_id
                LEFT JOIN reviews AS r ON r.assignment_id = ra.assignment_id
                WHERE ra.reviewer_id=%s AND r.review_id IS NULL
                ORDER BY ra.assigned_at DESC
            """, (session["user_id"],))
            assignments = cur.fetchall()
    except (MySQLError, RuntimeError) as error:
        app.logger.error(
            "Review page database operation failed: %s",
            type(error).__name__
        )
        return jsonify(error="Database temporarily unavailable"), 503

    return render_template(
        "reviews/review.html",
        assignments=assignments
    )


# =====================================================
# FINAL DECISIONS
# =====================================================

@app.route("/decisions")
@role_required("admin")
def decision_list():
    try:
        with cursor_scope(dictionary=True) as (conn, cur):
            cur.execute("""
                SELECT
                    p.paper_id, p.title, p.status, p.submitted_at,
                    COUNT(DISTINCT ra.assignment_id) AS assigned_reviews,
                    COUNT(DISTINCT r.review_id) AS completed_reviews
                FROM papers AS p
                LEFT JOIN review_assignments AS ra ON ra.paper_id=p.paper_id
                LEFT JOIN reviews AS r ON r.assignment_id=ra.assignment_id
                GROUP BY p.paper_id, p.title, p.status, p.submitted_at
                ORDER BY p.submitted_at DESC
                LIMIT 100
            """)
            papers_for_decision = cur.fetchall()
    except (MySQLError, RuntimeError) as error:
        app.logger.error(
            "Decision list database operation failed: %s",
            type(error).__name__
        )
        return jsonify(error="Decision data temporarily unavailable"), 503
    return render_template(
        "decisions/list.html",
        papers=papers_for_decision,
    )


@app.route("/decisions/<int:paper_id>", methods=["GET", "POST"])
@role_required("admin")
def record_decision(paper_id):
    if request.method == "POST":
        try:
            decision = request.form["decision"]
            if decision not in app.config["DECISION_VALUES"]:
                raise ValueError
            notes = _clean_text(
                request.form.get("decision_notes"),
                "Decision notes",
                app.config["MAX_DECISION_NOTES_LENGTH"],
            )
        except (KeyError, TypeError, ValueError):
            flash("Choose a valid decision and enter decision notes.", "danger")
            return redirect(url_for("record_decision", paper_id=paper_id))

        try:
            with cursor_scope(dictionary=True) as (conn, cur):
                cur.execute(
                    """
                    SELECT paper_id, title, author_id, status
                    FROM papers WHERE paper_id=%s
                    """,
                    (paper_id,),
                )
                paper = cur.fetchone()
                if not paper:
                    abort(404)
                cur.execute(
                    """
                    SELECT COUNT(*) AS assigned,
                           COUNT(r.review_id) AS completed
                    FROM review_assignments AS ra
                    LEFT JOIN reviews AS r ON r.assignment_id=ra.assignment_id
                    WHERE ra.paper_id=%s
                    """,
                    (paper_id,),
                )
                review_summary = cur.fetchone()
                if (
                    review_summary["assigned"] == 0
                    or review_summary["completed"] < review_summary["assigned"]
                ):
                    flash(
                        "All assigned reviews must be completed before deciding.",
                        "warning",
                    )
                    return redirect(
                        url_for("record_decision", paper_id=paper_id)
                    )
                cur.execute(
                    """
                    UPDATE papers
                    SET status=%s, decision_notes=%s, decided_by=%s,
                        decided_at=CURRENT_TIMESTAMP,
                        decision_released_at=CURRENT_TIMESTAMP
                    WHERE paper_id=%s
                    """,
                    (
                        decision,
                        notes,
                        session["user_id"],
                        paper_id,
                    ),
                )
                if paper["author_id"]:
                    _create_notification(
                        cur,
                        paper["author_id"],
                        "Paper decision released",
                        f"An official decision is available for paper #{paper_id}.",
                        url_for("paper_details", paper_id=paper_id),
                        f"decision-released:{paper_id}:{decision}",
                    )
                conn.commit()
        except (MySQLError, RuntimeError) as error:
            app.logger.error(
                "Decision recording database operation failed: %s",
                type(error).__name__
            )
            flash(
                "The decision could not be recorded. Please try again.",
                "danger",
            )
            return redirect(url_for("record_decision", paper_id=paper_id))
        flash("Official decision released successfully.", "success")
        return redirect(url_for("decision_list"))

    try:
        with cursor_scope(dictionary=True) as (conn, cur):
            cur.execute(
                """
                SELECT paper_id, title, abstract, status, author_id,
                       submitted_at, decision_notes, decided_at
                FROM papers WHERE paper_id=%s
                """,
                (paper_id,),
            )
            paper = cur.fetchone()
            if not paper:
                abort(404)
            cur.execute(
                """
                SELECT ra.assignment_id, u.full_name, r.overall_score,
                       r.recommendation, r.review_comment, r.reviewed_at
                FROM review_assignments AS ra
                JOIN users AS u ON u.user_id=ra.reviewer_id
                LEFT JOIN reviews AS r ON r.assignment_id=ra.assignment_id
                WHERE ra.paper_id=%s
                ORDER BY ra.assigned_at
                """,
                (paper_id,),
            )
            reviews = cur.fetchall()
    except (MySQLError, RuntimeError) as error:
        app.logger.error(
            "Decision details database operation failed: %s",
            type(error).__name__
        )
        return jsonify(error="Decision data temporarily unavailable"), 503
    return render_template(
        "decisions/detail.html",
        paper=paper,
        reviews=reviews,
    )


# =====================================================
# NOTIFICATIONS
# =====================================================

@app.route("/notifications")
@login_required
def notifications():
    try:
        with cursor_scope(dictionary=True) as (conn, cur):
            cur.execute(
                """
                SELECT notification_id, title, message, link, created_at, read_at
                FROM notifications
                WHERE recipient_id=%s
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (session["user_id"],),
            )
            user_notifications = cur.fetchall()
    except (MySQLError, RuntimeError) as error:
        app.logger.error(
            "Notification list database operation failed: %s",
            type(error).__name__
        )
        return jsonify(error="Notifications temporarily unavailable"), 503
    return render_template(
        "notifications/list.html",
        notifications=user_notifications,
    )


@app.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    try:
        with cursor_scope() as (conn, cur):
            cur.execute(
                """
                UPDATE notifications
                SET read_at=CURRENT_TIMESTAMP
                WHERE notification_id=%s AND recipient_id=%s
                """,
                (notification_id, session["user_id"]),
            )
            conn.commit()
    except (MySQLError, RuntimeError) as error:
        app.logger.error(
            "Notification update database operation failed: %s",
            type(error).__name__
        )
        return jsonify(error="Notification update unavailable"), 503
    return redirect(url_for("notifications"))


@app.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    try:
        with cursor_scope() as (conn, cur):
            cur.execute(
                """
                UPDATE notifications
                SET read_at=CURRENT_TIMESTAMP
                WHERE recipient_id=%s AND read_at IS NULL
                """,
                (session["user_id"],),
            )
            conn.commit()
    except (MySQLError, RuntimeError) as error:
        app.logger.error(
            "Notification bulk update database operation failed: %s",
            type(error).__name__
        )
        return jsonify(error="Notification update unavailable"), 503
    return redirect(url_for("notifications"))


@app.route("/papers/<int:paper_id>/download", methods=["GET"])
@login_required
def download_paper(paper_id):
    user = _current_user()
    try:
        with cursor_scope(dictionary=True) as (conn, cur):
            cur.execute(
                """
                SELECT uploaded_file_path
                FROM papers
                WHERE paper_id=%s
                """,
                (paper_id,),
            )
            paper = cur.fetchone()
            if not paper or not _paper_access_allowed(cur, paper_id, user):
                abort(404)
    except (MySQLError, RuntimeError):
        return jsonify(error="File temporarily unavailable"), 503

    if not paper or not paper["uploaded_file_path"]:
        abort(404)

    path = os.path.abspath(paper["uploaded_file_path"])
    upload_root = os.path.abspath(app.config["UPLOAD_FOLDER"])
    legacy_root = os.path.abspath(os.path.join(app.root_path, "static", "uploads"))
    if not any(
        os.path.commonpath([path, root]) == root
        for root in (upload_root, legacy_root)
    ):
        abort(404)
    if not os.path.isfile(path):
        abort(404)
    return send_file(path, as_attachment=False)



# =====================================================
# RUN APP
# =====================================================

if __name__ == "__main__":

    app.run(
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true"
    )