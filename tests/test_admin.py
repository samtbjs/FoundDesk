"""Admin access and rendering checks; SQL and concurrency need real PostgreSQL."""

import os
import secrets
import unittest
from datetime import date

os.environ.setdefault("SECRET_KEY", secrets.token_hex(32))

from flask import render_template, session
from app import app


class AdminTests(unittest.TestCase):
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

    def sign_in(self, role):
        with self.client.session_transaction() as current_session:
            current_session.update(user_id=1, role=role, csrf_token="test-token")

    def test_admin_routes_require_login_and_admin_role(self):
        self.assertEqual(self.client.get("/admin").location, "/login")
        with self.client.session_transaction() as current_session:
            current_session["csrf_token"] = "test-token"
        for action in ("approve", "reject"):
            response = self.client.post(f"/admin/claims/1/{action}", data={"csrf_token": "test-token"})
            self.assertEqual(response.location, "/login")
        for role in ("student", "unknown", None):
            self.sign_in(role)
            self.assertEqual(self.client.get("/admin").status_code, 403)
            for action in ("approve", "reject"):
                response = self.client.post(f"/admin/claims/1/{action}", data={"csrf_token": "test-token"})
                self.assertEqual(response.status_code, 403)

    def test_decisions_require_post_and_csrf(self):
        self.sign_in("admin")
        for action in ("approve", "reject"):
            path = f"/admin/claims/1/{action}"
            self.assertEqual(self.client.get(path).status_code, 405)
            for data in ({}, {"csrf_token": "wrong"}):
                self.assertEqual(self.client.post(path, data=data).location, "/")

    def test_invalid_decision_and_claim_id(self):
        self.sign_in("admin")
        for path in ("/admin/claims/1/delete", "/admin/claims/0/approve",
                     "/admin/claims/2147483648/reject"):
            self.assertEqual(self.client.post(path, data={"csrf_token": "test-token"}).status_code, 404)

    def test_outage_does_not_show_empty_or_success(self):
        self.sign_in("admin")
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Admin claims are unavailable", response.data)
        self.assertNotIn(b"No pending claims", response.data)
        for action in ("approve", "reject"):
            response = self.client.post(f"/admin/claims/1/{action}", data={"csrf_token": "test-token"})
            self.assertEqual(response.status_code, 503)
            self.assertIn(b"decision could not be saved", response.data)
            self.assertNotIn(b"Claim approved", response.data)
            self.assertNotIn(b"Claim rejected", response.data)

    def test_dashboard_forms_links_and_escaping(self):
        # Template inputs, not a simulated query or stored claim.
        claim = dict(claim_id=3, lost_id=2, found_id=4, claimant_name="<b>Student</b>",
                     lost_item_name="Keys", found_item_name="Found keys",
                     claim_reason="<script>private</script>", claim_date=date(2026, 1, 1))
        with app.test_request_context():
            session.update(user_id=1, role="admin")
            html = render_template("admin.html", claims=[claim], error=None)
            for value in ("/admin/claims/3/approve", "/admin/claims/3/reject",
                          "/items/Lost/2", "/items/Found/4", "2026-01-01",
                          "&lt;b&gt;Student&lt;/b&gt;", "&lt;script&gt;private&lt;/script&gt;"):
                self.assertIn(value, html)
            self.assertEqual(html.count('name="csrf_token"'), 3)  # logout and two decisions
            self.assertIn("No pending claims", render_template("admin.html", claims=[], error=None))

    def test_admin_navigation_is_role_scoped(self):
        with app.test_request_context():
            for role in (None, "student", "admin"):
                session.clear()
                if role:
                    session.update(user_id=1, role=role)
                html = render_template("index.html", counts=None, database_error=None)
                self.assertEqual('href="/admin"' in html, role == "admin")


if __name__ == "__main__":
    unittest.main()
