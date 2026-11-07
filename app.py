import os

import psycopg
from flask import Flask, render_template

from db import get_connection

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")


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


if __name__ == "__main__":
    app.run()
