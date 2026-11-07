"""Found-item checks without PostgreSQL or a substitute database."""

import os
import secrets
import unittest
from datetime import date, timedelta

os.environ.setdefault("SECRET_KEY", secrets.token_hex(32))

from flask import render_template, session
from app import app, validate_item_report


class FoundItemTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = ""
        self.form = {
            "item_name": "Keys", "category_id": "1", "description": "Blue keyring",
            "location": "Library", "found_date": date.today().isoformat(),
        }

    def tearDown(self):
        if self.database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.database_url

    def sign_in_session(self):
        # Access tests use a session directly; successful database login is untested.
        with self.client.session_transaction() as current_session:
            current_session["user_id"] = 1
            current_session["role"] = "student"
            current_session["csrf_token"] = "test-token"

    def test_validation_uses_found_date(self):
        self.assertIsNone(validate_item_report(self.form, "found_date"))
        for field in self.form:
            self.assertIsNotNone(validate_item_report(dict(self.form, **{field: ""}), "found_date"))
        for value in ("2026-02-30", "bad-date", "20261107"):
            self.assertIsNotNone(validate_item_report(dict(self.form, found_date=value), "found_date"))
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(
            validate_item_report(dict(self.form, found_date=tomorrow), "found_date"),
            "Date found cannot be in the future.",
        )

    def test_routes_require_login(self):
        for path in ("/report-found", "/found-items/1/edit"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, "/login")
        self.client.get("/login")
        with self.client.session_transaction() as current_session:
            token = current_session["csrf_token"]
        response = self.client.post("/found-items/1/delete", data={"csrf_token": token})
        self.assertEqual(response.location, "/login")

    def test_post_requires_csrf_and_delete_rejects_get(self):
        self.sign_in_session()
        for path in ("/report-found", "/found-items/1/edit", "/found-items/1/delete"):
            response = self.client.post(path, data=self.form)
            self.assertEqual(response.location, "/")
            with self.client.session_transaction() as current_session:
                self.assertIn("Your form expired or was invalid", str(current_session["_flashes"]))
        self.assertEqual(self.client.get("/found-items/1/delete").status_code, 405)

    def test_database_unavailable_messages_and_preserved_input(self):
        self.sign_in_session()
        response = self.client.get("/report-found")
        self.assertIn(b"Found reports are unavailable", response.data)
        self.assertIn(b"disabled", response.data)
        data = dict(self.form, csrf_token="test-token")
        response = self.client.post("/report-found", data=data)
        self.assertIn(b"Blue keyring", response.data)
        self.assertNotIn(b"Found item reported successfully", response.data)
        response = self.client.get("/my-reports")
        self.assertIn(b"Found reports are currently unavailable", response.data)
        self.assertNotIn(b"You have not reported any found items", response.data)
        response = self.client.post("/found-items/1/delete", data={"csrf_token": "test-token"})
        self.assertEqual(response.location, "/my-reports")

    def test_found_form_category_selection_and_edit_action(self):
        # Template values only: no category or report is inserted into a database.
        with app.test_request_context("/report-found"):
            html = render_template(
                "found_item_form.html", form_data=self.form, found_id=3,
                categories=[{"category_id": 1, "category_name": "Keys"}],
                today=date.today().isoformat(), database_available=True,
            )
            self.assertIn('action="/found-items/3/edit"', html)
            self.assertIn('name="found_date"', html)
            self.assertIn('selected', html)
            self.assertIn('name="csrf_token"', html)

    def test_found_table_actions_and_escaping(self):
        report = dict(self.form, found_id=4, category_name="Keys", status="Available",
                      has_claims=False, item_name="<script>alert(1)</script>")
        with app.test_request_context("/my-reports"):
            session["user_id"] = 1
            html = render_template("my_reports.html", reports=[], found_reports=[report])
            self.assertIn('/found-items/4/edit', html)
            self.assertIn('/found-items/4/delete', html)
            self.assertIn('&lt;script&gt;', html)
            report.update(status="Returned", has_claims=True)
            html = render_template("my_reports.html", reports=[], found_reports=[report])
            self.assertNotIn('/found-items/4/edit', html)
            self.assertNotIn('/found-items/4/delete', html)
            self.assertIn('Deletion blocked by a claim', html)


if __name__ == "__main__":
    unittest.main()
