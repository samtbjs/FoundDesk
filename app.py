import os
import re
import secrets
from functools import wraps
from datetime import date

import psycopg
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_connection

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
if (not app.config["SECRET_KEY"] or not app.config["SECRET_KEY"].strip()
        or app.config["SECRET_KEY"].strip() == "replace_with_a_random_secret_key"):
    raise RuntimeError("Set SECRET_KEY to your own random value in .env before starting FoundDesk.")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


@app.template_global()
def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


@app.before_request
def check_csrf():
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        expected_token = session.get("csrf_token", "")
        submitted_token = request.form.get("csrf_token", "")
        if not expected_token or not secrets.compare_digest(
            expected_token.encode(), submitted_token.encode()
        ):
            flash("Your form expired or was invalid. Please open the form and try again.")
            return redirect(url_for("index"))


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/")
def index():
    counts = None
    database_error = None

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        (SELECT COUNT(*) FROM lost_items) AS lost_count,
                        (SELECT COUNT(*) FROM found_items) AS found_count
                """)
                counts = cursor.fetchone()
    except psycopg.Error:
        # Keep database credentials and internal errors out of the page.
        database_error = (
            "Item counts are unavailable. Check that PostgreSQL is running, "
            "DATABASE_URL is configured in .env, and database/schema.sql "
            "has been executed."
        )

    return render_template(
        "index.html", counts=counts, database_error=database_error
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        error = None

        if not full_name or len(full_name) > 100:
            error = "Enter a full name of 1 to 100 characters."
        elif len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            error = "Enter a valid email address."
        elif not 8 <= len(password) <= 128:
            error = "Use a password of 8 to 128 characters."
        elif password != confirm_password:
            error = "Passwords do not match."

        if error is None:
            try:
                with get_connection() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT user_id FROM users WHERE email = %s", (email,)
                        )
                        if cursor.fetchone() is not None:
                            error = "An account with this email already exists."
                        else:
                            cursor.execute(
                                """
                                INSERT INTO users (full_name, email, password_hash, role)
                                VALUES (%s, %s, %s, 'student')
                                """,
                                (full_name, email, generate_password_hash(password)),
                            )
                if error is None:
                    flash("Registration successful. Please log in.")
                    return redirect(url_for("login"))
            except psycopg.errors.UniqueViolation:
                # The UNIQUE constraint also handles simultaneous registrations.
                error = "An account with this email already exists."
            except psycopg.Error:
                error = "Registration is unavailable. Check the database connection and try again."

        flash(error)

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        error = None

        if not email or not password or len(email) > 254 or len(password) > 128:
            error = "Enter a valid email and password."
        else:
            try:
                with get_connection() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT user_id, password_hash, role
                            FROM users WHERE email = %s
                            """,
                            (email,),
                        )
                        user = cursor.fetchone()

                if user is None or not check_password_hash(user["password_hash"], password):
                    error = "Incorrect email or password."
                else:
                    session.clear()
                    session["user_id"] = user["user_id"]
                    session["role"] = user["role"]
                    flash("You are now logged in.")
                    return redirect(url_for("index"))
            except psycopg.Error:
                error = "Login is unavailable. Check the database connection and try again."

        flash(error)

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("index"))


def validate_item_report(form_data, date_field):
    if not form_data.get("item_name") or len(form_data["item_name"]) > 150:
        return "Enter an item name of 1 to 150 characters."
    if not form_data.get("description"):
        return "Enter a description."
    if not form_data.get("location") or len(form_data["location"]) > 200:
        return "Enter a location of 1 to 200 characters."
    try:
        category_id = int(form_data.get("category_id", ""))
        if not 1 <= category_id <= 2147483647:
            return "Choose a valid category."
    except ValueError:
        return "Choose a valid category."
    try:
        report_date = date.fromisoformat(form_data.get(date_field, ""))
        if report_date.isoformat() != form_data[date_field]:
            return "Enter a valid date in YYYY-MM-DD format."
    except ValueError:
        return "Enter a valid date in YYYY-MM-DD format."
    if report_date > date.today():
        label = "lost" if date_field == "lost_date" else "found"
        return f"Date {label} cannot be in the future."
    return None


@app.route("/report-lost", defaults={"lost_id": None}, methods=["GET", "POST"])
@app.route("/lost-items/<int:lost_id>/edit", methods=["GET", "POST"])
@login_required
def report_lost(lost_id):
    # Creation and editing share the same five fields and template.
    form_data = {}
    categories = []
    database_available = True
    if request.method == "POST":
        form_data = {
            field: request.form.get(field, "").strip()
            for field in ("item_name", "category_id", "description", "location", "lost_date")
        }

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT category_id, category_name FROM categories ORDER BY category_name")
                categories = cursor.fetchall()

                if lost_id is not None:
                    cursor.execute(
                        """
                        SELECT item_name, category_id, description, location, lost_date
                        FROM lost_items
                        WHERE lost_id = %s AND user_id = %s AND status = 'Lost'
                        """,
                        (lost_id, session["user_id"]),
                    )
                    report = cursor.fetchone()
                    if report is None:
                        flash("Report not found, not yours, or already resolved. It cannot be edited.")
                        return redirect(url_for("my_reports"))
                    if request.method == "GET":
                        form_data = report

                if not categories:
                    flash("No categories are available. Run database/sample_data.sql first.")

                if request.method == "POST":
                    error = validate_item_report(form_data, "lost_date")
                    if error is None and int(form_data["category_id"]) not in {
                        category["category_id"] for category in categories
                    }:
                        error = "Choose a category from the list."
                    if error:
                        flash(error)
                    else:
                        values = (
                            int(form_data["category_id"]), form_data["item_name"],
                            form_data["description"], form_data["location"],
                            date.fromisoformat(form_data["lost_date"]),
                        )
                        if lost_id is None:
                            cursor.execute(
                                """
                                INSERT INTO lost_items
                                    (category_id, item_name, description, location,
                                     lost_date, user_id, status)
                                VALUES (%s, %s, %s, %s, %s, %s, 'Lost')
                                """,
                                values + (session["user_id"],),
                            )
                        else:
                            cursor.execute(
                                """
                                UPDATE lost_items
                                SET category_id = %s, item_name = %s, description = %s,
                                    location = %s, lost_date = %s
                                WHERE lost_id = %s AND user_id = %s AND status = 'Lost'
                                RETURNING lost_id
                                """,
                                values + (lost_id, session["user_id"]),
                            )
                            if cursor.fetchone() is None:
                                flash("Report is no longer available for editing.")
                                return redirect(url_for("my_reports"))
        # Exiting both with blocks commits before showing success.
        if request.method == "POST" and not error:
            flash("Lost item reported successfully." if lost_id is None else "Report updated successfully.")
            return redirect(url_for("my_reports"))
    except psycopg.errors.ForeignKeyViolation:
        flash("The category or account is no longer available. Refresh and try again.")
    except psycopg.Error:
        database_available = False
        flash("Lost reports are unavailable. Check the database connection and schema, then try again.")

    return render_template(
        "lost_item_form.html", form_data=form_data, categories=categories,
        lost_id=lost_id, today=date.today().isoformat(),
        database_available=database_available,
    )


@app.route("/my-reports")
@login_required
def my_reports():
    reports = None
    found_reports = None
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT l.lost_id, l.item_name, c.category_name, l.description,
                           l.location, l.lost_date, l.status,
                           EXISTS (SELECT 1 FROM claims WHERE lost_id = l.lost_id) AS has_claims
                    FROM lost_items AS l
                    JOIN categories AS c ON c.category_id = l.category_id
                    WHERE l.user_id = %s
                    ORDER BY l.lost_date DESC, l.lost_id DESC
                    """,
                    (session["user_id"],),
                )
                reports = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT f.found_id, f.item_name, c.category_name, f.description,
                           f.location, f.found_date, f.status,
                           EXISTS (SELECT 1 FROM claims WHERE found_id = f.found_id) AS has_claims
                    FROM found_items AS f
                    JOIN categories AS c ON c.category_id = f.category_id
                    WHERE f.user_id = %s
                    ORDER BY f.found_date DESC, f.found_id DESC
                    """,
                    (session["user_id"],),
                )
                found_reports = cursor.fetchall()
    except psycopg.Error:
        flash("Your reports could not be loaded. Check the database connection and try again.")
    return render_template("my_reports.html", reports=reports, found_reports=found_reports)


@app.route("/lost-items/<int:lost_id>/delete", methods=["POST"])
@login_required
def delete_lost_item(lost_id):
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM lost_items
                    WHERE lost_id = %s AND user_id = %s
                      AND NOT EXISTS (
                          SELECT 1 FROM claims WHERE claims.lost_id = lost_items.lost_id
                      )
                    RETURNING lost_id
                    """,
                    (lost_id, session["user_id"]),
                )
                deleted = cursor.fetchone()
        if deleted:
            flash("Lost report deleted successfully.")
        else:
            flash("Report not found, not yours, or referenced by a claim. It cannot be deleted.")
    except psycopg.errors.ForeignKeyViolation:
        flash("This report is referenced by a claim and cannot be deleted.")
    except psycopg.Error:
        flash("Report could not be deleted. Check the database connection and try again.")
    return redirect(url_for("my_reports"))


@app.route("/report-found", defaults={"found_id": None}, methods=["GET", "POST"])
@app.route("/found-items/<int:found_id>/edit", methods=["GET", "POST"])
@login_required
def report_found(found_id):
    form_data = {}
    categories = []
    database_available = True
    if request.method == "POST":
        form_data = {
            field: request.form.get(field, "").strip()
            for field in ("item_name", "category_id", "description", "location", "found_date")
        }

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT category_id, category_name FROM categories ORDER BY category_name")
                categories = cursor.fetchall()

                if found_id is not None:
                    cursor.execute(
                        """
                        SELECT item_name, category_id, description, location, found_date
                        FROM found_items
                        WHERE found_id = %s AND user_id = %s AND status = 'Available'
                        """,
                        (found_id, session["user_id"]),
                    )
                    report = cursor.fetchone()
                    if report is None:
                        flash("Report not found, not yours, or already returned. It cannot be edited.")
                        return redirect(url_for("my_reports"))
                    if request.method == "GET":
                        form_data = report

                if not categories:
                    flash("No categories are available. Run database/sample_data.sql first.")

                if request.method == "POST":
                    error = validate_item_report(form_data, "found_date")
                    if error is None and int(form_data["category_id"]) not in {
                        category["category_id"] for category in categories
                    }:
                        error = "Choose a category from the list."
                    if error:
                        flash(error)
                    else:
                        values = (
                            int(form_data["category_id"]), form_data["item_name"],
                            form_data["description"], form_data["location"],
                            date.fromisoformat(form_data["found_date"]),
                        )
                        if found_id is None:
                            cursor.execute(
                                """
                                INSERT INTO found_items
                                    (category_id, item_name, description, location,
                                     found_date, user_id, status)
                                VALUES (%s, %s, %s, %s, %s, %s, 'Available')
                                """,
                                values + (session["user_id"],),
                            )
                        else:
                            cursor.execute(
                                """
                                UPDATE found_items
                                SET category_id = %s, item_name = %s, description = %s,
                                    location = %s, found_date = %s
                                WHERE found_id = %s AND user_id = %s AND status = 'Available'
                                RETURNING found_id
                                """,
                                values + (found_id, session["user_id"]),
                            )
                            if cursor.fetchone() is None:
                                flash("Report is no longer available for editing.")
                                return redirect(url_for("my_reports"))
        # Show success only after the connection context commits the write.
        if request.method == "POST" and not error:
            flash("Found item reported successfully." if found_id is None else "Report updated successfully.")
            return redirect(url_for("my_reports"))
    except psycopg.errors.ForeignKeyViolation:
        flash("The category or account is no longer available. Refresh and try again.")
    except psycopg.Error:
        database_available = False
        flash("Found reports are unavailable. Check the database connection and schema, then try again.")

    return render_template(
        "found_item_form.html", form_data=form_data, categories=categories,
        found_id=found_id, today=date.today().isoformat(),
        database_available=database_available,
    )


@app.route("/found-items/<int:found_id>/delete", methods=["POST"])
@login_required
def delete_found_item(found_id):
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM found_items
                    WHERE found_id = %s AND user_id = %s
                      AND NOT EXISTS (
                          SELECT 1 FROM claims WHERE claims.found_id = found_items.found_id
                      )
                    RETURNING found_id
                    """,
                    (found_id, session["user_id"]),
                )
                deleted = cursor.fetchone()
        if deleted:
            flash("Found report deleted successfully.")
        else:
            flash("Report not found, not yours, or referenced by a claim. It cannot be deleted.")
    except psycopg.errors.ForeignKeyViolation:
        flash("This report is referenced by a claim and cannot be deleted.")
    except psycopg.Error:
        flash("Report could not be deleted. Check the database connection and try again.")
    return redirect(url_for("my_reports"))


@app.route("/browse-items")
@login_required
def browse_items():
    filters = {
        name: request.args.get(name, "").strip()
        for name in ("keyword", "category_id", "location")
    }
    filters["type"] = request.args.get("type", "All").strip()
    categories = []
    items = None
    error = None
    category_id = None
    if filters["type"] not in ("All", "Lost", "Found"):
        error = "Choose All, Lost, or Found as the item type."
    elif len(filters["keyword"]) > 150 or len(filters["location"]) > 200:
        error = "Use at most 150 characters for keyword and 200 for location."
    elif filters["category_id"]:
        try:
            category_id = int(filters["category_id"])
            if not 1 <= category_id <= 2147483647:
                error = "Choose a valid category."
        except ValueError:
            error = "Choose a valid category."
    if error:
        return render_template(
            "browse_items.html", filters=filters, categories=categories,
            items=items, error=error,
        ), 400

    # Only fixed SQL fragments are joined; every user value is bound separately.
    conditions = []
    values = []
    if filters["keyword"]:
        conditions.append("i.item_name ILIKE %s")
        values.append("%" + filters["keyword"] + "%")
    if category_id is not None:
        conditions.append("i.category_id = %s")
        values.append(category_id)
    if filters["location"]:
        conditions.append("i.location ILIKE %s")
        values.append("%" + filters["location"] + "%")
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT category_id, category_name FROM categories ORDER BY category_name")
                categories = cursor.fetchall()
                if category_id is not None and category_id not in {
                    category["category_id"] for category in categories
                }:
                    return render_template(
                        "browse_items.html", filters=filters, categories=categories,
                        items=None, error="Choose a category from the list.",
                    ), 400
                items = []
                if filters["type"] in ("All", "Lost"):
                    cursor.execute(
                        """
                        SELECT i.lost_id AS item_id, i.item_name, c.category_name,
                               i.location, i.lost_date AS item_date, i.status,
                               'Lost' AS item_type
                        FROM lost_items AS i
                        JOIN categories AS c ON c.category_id = i.category_id
                        """ + where_clause + " ORDER BY i.lost_date DESC, i.lost_id DESC",
                        values,
                    )
                    items.extend(cursor.fetchall())
                if filters["type"] in ("All", "Found"):
                    cursor.execute(
                        """
                        SELECT i.found_id AS item_id, i.item_name, c.category_name,
                               i.location, i.found_date AS item_date, i.status,
                               'Found' AS item_type
                        FROM found_items AS i
                        JOIN categories AS c ON c.category_id = i.category_id
                        """ + where_clause + " ORDER BY i.found_date DESC, i.found_id DESC",
                        values,
                    )
                    items.extend(cursor.fetchall())
                # Merge the two result lists by event date, newest first.
                items.sort(key=lambda item: (item["item_date"], item["item_id"], item["item_type"]), reverse=True)
    except psycopg.Error:
        items = None
        error = "Items are unavailable. Check the database connection and schema, then try again."
    return render_template(
        "browse_items.html", filters=filters, categories=categories,
        items=items, error=error,
    ), 503 if error else 200


@app.route("/items/<item_type>/<int:item_id>")
@login_required
def item_detail(item_type, item_id):
    if item_type not in ("Lost", "Found") or not 1 <= item_id <= 2147483647:
        abort(404)
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                if item_type == "Lost":
                    query = """
                        SELECT i.item_name, i.description, c.category_name,
                               i.location, i.lost_date AS item_date, i.status
                        FROM lost_items AS i
                        JOIN categories AS c ON c.category_id = i.category_id
                        WHERE i.lost_id = %s
                    """
                else:
                    query = """
                        SELECT i.found_id, i.user_id, i.item_name, i.description, c.category_name,
                               i.location, i.found_date AS item_date, i.status
                        FROM found_items AS i
                        JOIN categories AS c ON c.category_id = i.category_id
                        WHERE i.found_id = %s
                    """
                cursor.execute(query, (item_id,))
                item = cursor.fetchone()
    except psycopg.Error:
        return render_template(
            "item_detail.html", item=None, item_type=item_type,
            error="Item details are unavailable. Check the database connection and try again.",
        ), 503
    if item is None:
        abort(404)
    return render_template("item_detail.html", item=item, item_type=item_type, error=None)


def validate_claim_form(form_data):
    try:
        lost_id = int(form_data.get("lost_id", ""))
        if not 1 <= lost_id <= 2147483647:
            return "Choose a valid lost report."
    except ValueError:
        return "Choose a valid lost report."
    reason = form_data.get("claim_reason", "").strip()
    if not reason or len(reason) > 2000:
        return "Enter a claim reason of 1 to 2000 characters."
    return None


@app.route("/found-items/<int:found_id>/claim", methods=["GET", "POST"])
@login_required
def submit_claim(found_id):
    if session.get("role") != "student":
        abort(403)
    if not 1 <= found_id <= 2147483647:
        abort(404)
    form_data = {
        "lost_id": request.form.get("lost_id", "").strip(),
        "claim_reason": request.form.get("claim_reason", "").strip(),
    }
    found_item = None
    lost_reports = []
    error = None
    response_status = 200
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                # Hold the found row during POST so eligibility cannot change mid-insert.
                query = """
                    SELECT found_id, item_name, user_id, status
                    FROM found_items WHERE found_id = %s
                """
                if request.method == "POST":
                    query += " FOR UPDATE"
                cursor.execute(query, (found_id,))
                found_item = cursor.fetchone()
                if found_item is None:
                    abort(404)
                if found_item["user_id"] == session["user_id"]:
                    abort(403)
                if found_item["status"] != "Available":
                    error = "This found item is no longer available for claims."
                    response_status = 409
                else:
                    cursor.execute(
                        """
                        SELECT lost_id, item_name, lost_date
                        FROM lost_items
                        WHERE user_id = %s AND status = 'Lost'
                        ORDER BY lost_date DESC, lost_id DESC
                        """,
                        (session["user_id"],),
                    )
                    lost_reports = cursor.fetchall()
                    if request.method == "POST":
                        error = validate_claim_form(form_data)
                        response_status = 400 if error else 200
                        if error is None:
                            cursor.execute(
                                """
                                SELECT lost_id FROM lost_items
                                WHERE lost_id = %s AND user_id = %s AND status = 'Lost'
                                FOR UPDATE
                                """,
                                (int(form_data["lost_id"]), session["user_id"]),
                            )
                            if cursor.fetchone() is None:
                                error = "Choose one of your own unresolved lost reports."
                                response_status = 400
                        if error is None:
                            cursor.execute(
                                """
                                SELECT claim_id FROM claims
                                WHERE lost_id = %s AND found_id = %s
                                """,
                                (int(form_data["lost_id"]), found_id),
                            )
                            if cursor.fetchone() is not None:
                                error = "A claim already exists for this lost/found pair."
                                response_status = 409
                        if error is None:
                            cursor.execute(
                                """
                                INSERT INTO claims
                                    (lost_id, found_id, claimant_id, claim_reason, claim_date, status)
                                VALUES (%s, %s, %s, %s, CURRENT_DATE, 'Pending')
                                """,
                                (int(form_data["lost_id"]), found_id,
                                 session["user_id"], form_data["claim_reason"]),
                            )
        # The transaction must commit before the success redirect.
        if request.method == "POST" and error is None:
            flash("Claim submitted successfully with Pending status.")
            return redirect(url_for("my_claims"))
    except psycopg.errors.UniqueViolation:
        error = "A claim already exists for this lost/found pair."
        response_status = 409
    except psycopg.errors.ForeignKeyViolation:
        error = "A report or account is no longer available. Refresh and try again."
        response_status = 409
    except psycopg.Error:
        error = "Claims are unavailable. Check the database connection and try again."
        response_status = 503
    return render_template(
        "claim_form.html", found_item=found_item, lost_reports=lost_reports,
        form_data=form_data, error=error, database_available=response_status != 503,
    ), response_status


@app.route("/my-claims")
@login_required
def my_claims():
    claims = None
    error = None
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT c.claim_id, c.lost_id, c.found_id, c.claim_reason,
                           c.claim_date, c.status, l.item_name AS lost_item_name,
                           f.item_name AS found_item_name
                    FROM claims AS c
                    JOIN lost_items AS l ON l.lost_id = c.lost_id
                    JOIN found_items AS f ON f.found_id = c.found_id
                    WHERE c.claimant_id = %s
                    ORDER BY c.claim_date DESC, c.claim_id DESC
                    """,
                    (session["user_id"],),
                )
                claims = cursor.fetchall()
    except psycopg.Error:
        error = "Your claims are unavailable. Check the database connection and try again."
    return render_template("my_claims.html", claims=claims, error=error), 503 if error else 200


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped_view(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/admin")
@admin_required
def admin_dashboard():
    claims = None
    totals = None
    error = None
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                totals = load_report_totals(cursor)
                cursor.execute(
                    """
                    SELECT c.claim_id, c.lost_id, c.found_id, c.claim_reason,
                           c.claim_date, u.full_name AS claimant_name,
                           l.item_name AS lost_item_name, f.item_name AS found_item_name
                    FROM claims AS c
                    JOIN users AS u ON u.user_id = c.claimant_id
                    JOIN lost_items AS l ON l.lost_id = c.lost_id
                    JOIN found_items AS f ON f.found_id = c.found_id
                    WHERE c.status = 'Pending'
                    ORDER BY c.claim_date, c.claim_id
                    """
                )
                claims = cursor.fetchall()
    except psycopg.Error:
        error = "Admin claims are unavailable. Check the database connection and try again."
    return render_template("admin.html", claims=claims, totals=totals, error=error), 503 if error else 200


@app.route("/admin/claims/<int:claim_id>/<decision>", methods=["POST"])
@admin_required
def decide_claim(claim_id, decision):
    if decision not in ("approve", "reject") or not 1 <= claim_id <= 2147483647:
        abort(404)
    try:
        # All writes below commit together, or roll back on any exception.
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT lost_id, found_id, claimant_id FROM claims WHERE claim_id = %s",
                    (claim_id,),
                )
                claim = cursor.fetchone()
                if claim is None:
                    abort(404)
                if decision == "reject":
                    cursor.execute(
                        """
                        UPDATE claims SET status = 'Rejected'
                        WHERE claim_id = %s AND status = 'Pending'
                        RETURNING claim_id
                        """,
                        (claim_id,),
                    )
                    if cursor.fetchone() is None:
                        abort(409, description="This claim has already been decided. Refresh the dashboard.")
                else:
                    # Use the same item lock order as claim submission: found, then lost.
                    cursor.execute(
                        "SELECT user_id, status FROM found_items WHERE found_id = %s FOR UPDATE",
                        (claim["found_id"],),
                    )
                    found_item = cursor.fetchone()
                    cursor.execute(
                        "SELECT user_id, status FROM lost_items WHERE lost_id = %s FOR UPDATE",
                        (claim["lost_id"],),
                    )
                    lost_item = cursor.fetchone()
                    # Lock overlapping claims by ID so competing decisions use a common order.
                    cursor.execute(
                        """
                        SELECT claim_id, status FROM claims
                        WHERE found_id = %s OR lost_id = %s
                        ORDER BY claim_id FOR UPDATE
                        """,
                        (claim["found_id"], claim["lost_id"]),
                    )
                    related_claims = cursor.fetchall()
                    selected_claim = next(
                        (row for row in related_claims if row["claim_id"] == claim_id), None
                    )
                    if selected_claim is None or selected_claim["status"] != "Pending":
                        abort(409, description="This claim has already been decided. Refresh the dashboard.")
                    if (found_item is None or lost_item is None
                            or found_item["status"] != "Available" or lost_item["status"] != "Lost"
                            or lost_item["user_id"] != claim["claimant_id"]
                            or found_item["user_id"] == claim["claimant_id"]
                            or any(row["status"] == "Approved" for row in related_claims)):
                        abort(409, description="This claim conflicts with an approved claim or ineligible item. Refresh the dashboard.")
                    cursor.execute(
                        "UPDATE claims SET status = 'Approved' WHERE claim_id = %s",
                        (claim_id,),
                    )
                    cursor.execute(
                        "UPDATE found_items SET status = 'Returned' WHERE found_id = %s",
                        (claim["found_id"],),
                    )
                    cursor.execute(
                        "UPDATE lost_items SET status = 'Resolved' WHERE lost_id = %s",
                        (claim["lost_id"],),
                    )
                    cursor.execute(
                        """
                        UPDATE claims SET status = 'Rejected'
                        WHERE claim_id <> %s AND status = 'Pending'
                          AND (found_id = %s OR lost_id = %s)
                        """,
                        (claim_id, claim["found_id"], claim["lost_id"]),
                    )
        flash("Claim approved and conflicting pending claims rejected. Items marked Returned and Resolved."
              if decision == "approve" else "Claim rejected. Item statuses were not changed.")
        return redirect(url_for("admin_dashboard"))
    except psycopg.Error:
        return render_template(
            "admin.html", claims=None,
            error="The claim decision could not be saved. Refresh the dashboard and check its current status before trying again.",
        ), 503


def load_report_totals(cursor):
    cursor.execute(
        """
        SELECT (SELECT COUNT(*) FROM lost_items) AS lost_count,
               (SELECT COUNT(*) FROM found_items) AS found_count,
               (SELECT COUNT(*) FROM claims WHERE status = 'Pending') AS pending_count,
               (SELECT COUNT(*) FROM found_items WHERE status = 'Returned') AS returned_count
        """
    )
    return cursor.fetchone()


@app.route("/reports")
@admin_required
def reports():
    totals = None
    category_counts = []
    claim_counts = []
    unresolved_items = []
    returned_items = []
    error = None
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                totals = load_report_totals(cursor)
                # Aggregate each item table first so joins cannot multiply counts.
                cursor.execute(
                    """
                    SELECT c.category_name, COALESCE(l.lost_count, 0) AS lost_count,
                           COALESCE(f.found_count, 0) AS found_count
                    FROM categories AS c
                    LEFT JOIN (
                        SELECT category_id, COUNT(*) AS lost_count FROM lost_items GROUP BY category_id
                    ) AS l ON l.category_id = c.category_id
                    LEFT JOIN (
                        SELECT category_id, COUNT(*) AS found_count FROM found_items GROUP BY category_id
                    ) AS f ON f.category_id = c.category_id
                    ORDER BY c.category_name
                    """
                )
                category_counts = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT s.status, COUNT(c.claim_id) AS claim_count
                    FROM (VALUES ('Pending'), ('Approved'), ('Rejected')) AS s(status)
                    LEFT JOIN claims AS c ON c.status = s.status
                    GROUP BY s.status ORDER BY s.status
                    """
                )
                claim_counts = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT l.lost_id, l.item_name, c.category_name, l.location, l.lost_date
                    FROM lost_items AS l
                    INNER JOIN categories AS c ON c.category_id = l.category_id
                    WHERE l.status = 'Lost' ORDER BY l.lost_date DESC, l.lost_id DESC
                    """
                )
                unresolved_items = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT f.found_id, f.item_name, c.category_name, f.location, f.found_date
                    FROM found_items AS f
                    INNER JOIN categories AS c ON c.category_id = f.category_id
                    WHERE f.status = 'Returned' ORDER BY f.found_date DESC, f.found_id DESC
                    """
                )
                returned_items = cursor.fetchall()
    except psycopg.Error:
        error = "Reports are unavailable. Check the database connection and schema, then try again."
    return render_template(
        "reports.html", totals=totals, category_counts=category_counts,
        claim_counts=claim_counts, unresolved_items=unresolved_items,
        returned_items=returned_items, error=error,
    ), 503 if error else 200


if __name__ == "__main__":
    app.run()
