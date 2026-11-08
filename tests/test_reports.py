"""Report access and HTML checks without SQL execution or database substitutes."""

import os
import secrets
import unittest
from datetime import date

os.environ.setdefault("SECRET_KEY", secrets.token_hex(32))

from flask import render_template, session
from app import app


class ReportTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = ""

    def tearDown(self):
        if self.database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.database_url

    def test_reports_require_admin(self):
        self.assertEqual(self.client.get("/reports").location, "/login")
        for role in ("student", None):
            with self.client.session_transaction() as current_session:
                current_session.update(user_id=1, role=role)
            self.assertEqual(self.client.get("/reports").status_code, 403)

    def test_outage_is_not_zero_totals(self):
        with self.client.session_transaction() as current_session:
            current_session.update(user_id=1, role="admin")
        for path in ("/admin", "/reports"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 503)
            self.assertNotIn(b"<h3>Totals</h3>", response.data)
            self.assertNotIn(b"No unresolved lost items", response.data)
        self.assertIn(b"Reports are unavailable", self.client.get("/reports").data)

    def test_render_tables_links_escaping_and_no_private_fields(self):
        # Inputs exercise templates only; these are not simulated database rows.
        totals = dict(lost_count=2, found_count=3, pending_count=1, returned_count=1)
        item = dict(lost_id=2, found_id=4, item_name="<b>Keys</b>", category_name="Keys",
                    location="Library", lost_date=date(2026, 1, 1), found_date=date(2026, 1, 2),
                    claim_reason="PRIVATE SENTINEL", password_hash="HASH SENTINEL")
        with app.test_request_context():
            session.update(user_id=1, role="admin")
            html = render_template("reports.html", totals=totals,
                                   category_counts=[dict(category_name="Keys", lost_count=2, found_count=3)],
                                   claim_counts=[dict(status="Pending", claim_count=1)],
                                   unresolved_items=[item], returned_items=[item], error=None)
            for value in ("/items/Lost/2", "/items/Found/4", "&lt;b&gt;Keys&lt;/b&gt;",
                          "2026-01-01", "2026-01-02", "Claim Status Counts", "Date found"):
                self.assertIn(value, html)
            self.assertNotIn("PRIVATE SENTINEL", html)
            self.assertNotIn("HASH SENTINEL", html)
            admin_html = render_template("admin.html", claims=[], totals=totals, error=None)
            self.assertIn("<td>2</td><td>3</td><td>1</td><td>1</td>", admin_html)

    def test_zero_and_partial_failure_rendering(self):
        with app.test_request_context():
            context = dict(totals=dict(lost_count=0, found_count=0, pending_count=0, returned_count=0),
                           category_counts=[], claim_counts=[dict(status=s, claim_count=0)
                                                            for s in ("Pending", "Approved", "Rejected")],
                           unresolved_items=[], returned_items=[], error=None)
            html = render_template("reports.html", **context)
            for value in ("No categories", "No unresolved lost items", "No returned items",
                          "Pending", "Approved", "Rejected", "<td>0</td>"):
                self.assertIn(value, html)
            html = render_template("reports.html", **dict(context, error="Reports are unavailable"))
            self.assertNotIn("<h3>Totals</h3>", html)
            self.assertNotIn("No returned items", html)

    def test_report_navigation_scoped_to_admin(self):
        with app.test_request_context():
            for role in (None, "student", "admin"):
                session.clear()
                if role:
                    session.update(user_id=1, role=role)
                html = render_template("index.html", counts=None, database_error=None)
                self.assertEqual('href="/reports"' in html, role == "admin")


if __name__ == "__main__":
    unittest.main()
