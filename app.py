from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from db import get_connection

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename

import os

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

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER



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

        full_name = request.form["full_name"]

        email = request.form["email"]

        password = request.form["password"]

        role = request.form["role"]

        hashed_password = generate_password_hash(password)

        conn = get_connection()

        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM users
            WHERE email=%s
        """, (email,))

        existing_user = cur.fetchone()

        if existing_user:

            flash(
                "Email already exists!",
                "warning"
            )

            conn.close()

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
            role
        ))

        conn.commit()

        conn.close()

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

        email = request.form["email"]

        password = request.form["password"]

        conn = get_connection()

        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT * FROM users
            WHERE email=%s
        """, (email,))

        user = cur.fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["user_id"]

            session["full_name"] = user["full_name"]

            session["role"] = user["role"]

            flash(
                "Login successful!",
                "success"
            )

            # ROLE BASED DASHBOARD
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

            elif user["role"] == "reviewer":
                return redirect(url_for("reviewer_dashboard"))

            else:
                return redirect(url_for("author_dashboard"))

        else:

            flash(
                "Invalid email or password!",
                "danger"
            )

    return render_template("auth/login.html")



# =====================================================
# LOGOUT
# =====================================================

@app.route("/logout")
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
def admin_dashboard():

    conn = get_connection()

    cur = conn.cursor(dictionary=True)

    # TOTAL PAPERS
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM papers
    """)

    total_papers = cur.fetchone()["total"]

    # ACCEPTED PAPERS
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM papers
        WHERE status='Accepted'
    """)

    accepted_papers = cur.fetchone()["total"]

    # REJECTED PAPERS
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM papers
        WHERE status='Rejected'
    """)

    rejected_papers = cur.fetchone()["total"]

    # TOTAL REVIEWERS
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM users
        WHERE role='reviewer'
    """)

    total_reviewers = cur.fetchone()["total"]

    conn.close()

    return render_template(
        "dashboard/admin_dashboard.html",
        total_papers=total_papers,
        accepted_papers=accepted_papers,
        rejected_papers=rejected_papers,
        total_reviewers=total_reviewers
    )



# =====================================================
# REVIEWER DASHBOARD
# =====================================================

@app.route("/reviewer_dashboard")
def reviewer_dashboard():

    return render_template(
        "dashboard/reviewer_dashboard.html"
    )



# =====================================================
# AUTHOR DASHBOARD
# =====================================================

@app.route("/author_dashboard")
def author_dashboard():

    return render_template(
        "dashboard/author_dashboard.html"
    )



# =====================================================
# SUBMIT PAPER
# =====================================================

@app.route(
    "/submit_paper",
    methods=["GET", "POST"]
)
def submit_paper():

    if request.method == "POST":

        title = request.form["title"]

        abstract = request.form["abstract"]

        keywords = request.form["keywords"]

        paper_file = request.files["paper_file"]

        filename = secure_filename(
            paper_file.filename
        )

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        paper_file.save(filepath)

        conn = get_connection()

        cur = conn.cursor()

        cur.execute("""
            INSERT INTO papers
            (
                title,
                abstract,
                keywords,
                file_name,
                uploaded_file_path
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            title,
            abstract,
            keywords,
            filename,
            filepath
        ))

        conn.commit()

        conn.close()

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
def papers():

    conn = get_connection()

    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT *
        FROM papers
        ORDER BY submitted_at DESC
    """)

    papers = cur.fetchall()

    conn.close()

    return render_template(
        "papers/papers.html",
        papers=papers
    )



# =====================================================
# REVIEWERS
# =====================================================

@app.route("/reviewers")
def reviewers():

    conn = get_connection()

    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT *
        FROM users
        WHERE role='reviewer'
    """)

    reviewers = cur.fetchall()

    conn.close()

    return render_template(
        "reviewers/reviewers.html",
        reviewers=reviewers
    )



# =====================================================
# ASSIGN REVIEWER
# =====================================================

@app.route("/assign", methods=["GET", "POST"])
def assign():

    # DATABASE CONNECTION
    conn = get_connection()

    # CURSOR
    cur = conn.cursor(dictionary=True)

    # =================================================
    # HANDLE FORM SUBMISSION
    # =================================================

    if request.method == "POST":

        # GET FORM DATA
        paper_id = request.form["paper_id"]

        reviewer_id = request.form["reviewer_id"]

        # =================================================
        # CHECK IF REVIEWER ALREADY ASSIGNED
        # =================================================

        cur.execute("""
            SELECT *
            FROM review_assignments
            WHERE paper_id = %s
            AND reviewer_id = %s
        """, (
            paper_id,
            reviewer_id
        ))

        existing_assignment = cur.fetchone()

        # =================================================
        # IF REVIEWER ALREADY ASSIGNED
        # =================================================

        if existing_assignment:

            flash(
                "Reviewer already assigned to this paper!",
                "warning"
            )

        else:

            # =================================================
            # INSERT NEW ASSIGNMENT
            # =================================================

            cur.execute("""
                INSERT INTO review_assignments
                (
                    paper_id,
                    reviewer_id
                )
                VALUES (%s, %s)
            """, (
                paper_id,
                reviewer_id
            ))

            # =================================================
            # UPDATE PAPER STATUS
            # =================================================

            cur.execute("""
                UPDATE papers
                SET status = 'Under Review'
                WHERE paper_id = %s
            """, (
                paper_id,
            ))

            # =================================================
            # SAVE CHANGES
            # =================================================

            conn.commit()

            flash(
                "Reviewer assigned successfully!",
                "success"
            )

        # =================================================
        # CLOSE CONNECTION
        # =================================================

        conn.close()

        return redirect(
            url_for("admin_dashboard")
        )

    # =================================================
    # FETCH ALL PAPERS
    # =================================================

    cur.execute("""
        SELECT *
        FROM papers
        ORDER BY submitted_at DESC
    """)

    papers = cur.fetchall()

    # =================================================
    # FETCH ALL REVIEWERS
    # =================================================

    cur.execute("""
        SELECT *
        FROM users
        WHERE role = 'reviewer'
    """)

    reviewers = cur.fetchall()

    # =================================================
    # CLOSE CONNECTION
    # =================================================

    conn.close()

    # =================================================
    # RENDER TEMPLATE
    # =================================================

    return render_template(
        "reviews/assign.html",
        papers=papers,
        reviewers=reviewers
    )

# =====================================================
# SUBMIT REVIEW
# =====================================================

@app.route(
    "/review",
    methods=["GET", "POST"]
)
def review():

    conn = get_connection()

    cur = conn.cursor(dictionary=True)

    if request.method == "POST":

        assignment_id = request.form["assignment_id"]

        technical_merit = float(
            request.form["technical_merit"]
        )

        readability = float(
            request.form["readability"]
        )

        originality = float(
            request.form["originality"]
        )

        relevance = float(
            request.form["relevance"]
        )

        recommendation = request.form[
            "recommendation"
        ]

        review_comment = request.form[
            "review_comment"
        ]

        overall_score = round(
            (
                technical_merit +
                readability +
                originality +
                relevance
            ) / 4,
            1
        )

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

        conn.commit()

        flash(
            "Review submitted successfully!",
            "success"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    cur.execute("""
        SELECT *
        FROM review_assignments
    """)

    assignments = cur.fetchall()

    conn.close()

    return render_template(
        "reviews/review.html",
        assignments=assignments
    )



# =====================================================
# RUN APP
# =====================================================

if __name__ == "__main__":

    app.run(
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true"
    )