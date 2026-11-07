import os
import re
import secrets
from functools import wraps

import psycopg
from flask import Flask, flash, redirect, render_template, request, session, url_for
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


if __name__ == "__main__":
    app.run()
