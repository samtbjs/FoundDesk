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
if not app.config["SECRET_KEY"]:
    raise RuntimeError("Set SECRET_KEY in .env before starting FoundDesk.")
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
                        SELECT i.item_name, i.description, c.category_name,
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


if __name__ == "__main__":
    app.run()
