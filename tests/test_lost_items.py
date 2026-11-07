"""Validation, access and template checks; no database is substituted."""

import os
import secrets
import unittest
from datetime import date, timedelta

os.environ.setdefault("SECRET_KEY", secrets.token_hex(32))

from flask import render_template, session
from app import app, validate_lost_item


class LostItemTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = ""
        self.form = {
            "item_name": "Notebook", "category_id": "1",
            "description": "Blue cover", "location": "Library",
            "lost_date": date.today().isoformat(),
        }

    def tearDown(self):
        if self.database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.database_url

    def sign_in_session(self):
        # This only sets a session for access tests; it does not test real login.
        with self.client.session_transaction() as current_session:
            current_session["user_id"] = 1
            current_session["role"] = "student"
            current_session["csrf_token"] = "test-token"

    def test_required_fields_and_lengths(self):
        self.assertIsNone(validate_lost_item(self.form))
        for field in self.form:
            with self.subTest(field=field):
                data = dict(self.form, **{field: ""})
                self.assertIsNotNone(validate_lost_item(data))
        for field, value in (("item_name", "x" * 151), ("location", "x" * 201),
                             ("category_id", "abc"), ("category_id", "0"),
                             ("category_id", "2147483648")):
            self.assertIsNotNone(validate_lost_item(dict(self.form, **{field: value})))

    def test_invalid_and_future_dates(self):
        for value in ("2026-02-30", "not-a-date", "20261107",
                      (date.today() + timedelta(days=1)).isoformat()):
            self.assertIsNotNone(validate_lost_item(dict(self.form, lost_date=value)))
        self.assertIsNone(validate_lost_item(dict(self.form, lost_date="2024-02-29")))

    def test_anonymous_routes_redirect_to_login(self):
        for path in ("/report-lost", "/my-reports", "/lost-items/1/edit"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, "/login")

    def test_post_requires_csrf_and_delete_rejects_get(self):
        self.sign_in_session()
        for path in ("/report-lost", "/lost-items/1/edit", "/lost-items/1/delete"):
            response = self.client.post(path, data=self.form)
            self.assertEqual(response.status_code, 302)
            with self.client.session_transaction() as current_session:
                messages = str(current_session.get("_flashes", []))
                self.assertIn("Your form expired or was invalid", messages)
        self.assertEqual(self.client.get("/lost-items/1/delete").status_code, 405)

    def test_missing_database_configuration_is_not_an_empty_report_list(self):
        self.sign_in_session()
        response = self.client.get("/report-lost")
        self.assertIn(b"Lost reports are unavailable", response.data)
        self.assertIn(b"disabled", response.data)
        response = self.client.get("/my-reports")
        self.assertIn(b"Reports are currently unavailable", response.data)
        self.assertNotIn(b"You have not reported any lost items", response.data)
        response = self.client.post("/lost-items/1/delete", data={"csrf_token": "test-token"})
        self.assertEqual(response.location, "/my-reports")
        with self.client.session_transaction() as current_session:
            self.assertIn("Report could not be deleted", str(current_session["_flashes"]))

    def test_table_actions_and_html_escaping(self):
        # Template input only: these rows are not inserted into any database.
        report = {
            "lost_id": 10, "item_name": "<script>alert(1)</script>",
            "category_name": "Books", "description": "Blue cover",
            "location": "Library", "lost_date": date.today(),
            "status": "Lost", "has_claims": False,
        }
        with app.test_request_context("/my-reports"):
            session["user_id"] = 1
            html = render_template("my_reports.html", reports=[report])
            self.assertIn('/lost-items/10/edit', html)
            self.assertIn('/lost-items/10/delete', html)
            self.assertIn('&lt;script&gt;', html)
            report.update(status="Resolved", has_claims=True)
            html = render_template("my_reports.html", reports=[report])
            self.assertNotIn('/lost-items/10/edit', html)
            self.assertNotIn('/lost-items/10/delete', html)
            self.assertIn('Deletion blocked by a claim', html)


if __name__ == "__main__":
    unittest.main()
