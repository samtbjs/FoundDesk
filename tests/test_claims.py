"""Claim validation, access and rendering checks without database substitutes."""

import os
import secrets
import unittest
from datetime import date

os.environ.setdefault("SECRET_KEY", secrets.token_hex(32))

from flask import render_template, session
from app import app, validate_claim_form


class ClaimTests(unittest.TestCase):
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

    def sign_in(self, role="student"):
        with self.client.session_transaction() as current_session:
            current_session.update(user_id=1, role=role, csrf_token="test-token")

    def test_reason_and_id_validation(self):
        valid = dict(lost_id="1", claim_reason="Blue keyring with my initials")
        self.assertIsNone(validate_claim_form(valid))
        for value in ("", "bad", "0", "-1", "2147483648"):
            self.assertIsNotNone(validate_claim_form(dict(valid, lost_id=value)))
        for value in ("", "  \n", "x" * 2001):
            self.assertIsNotNone(validate_claim_form(dict(valid, claim_reason=value)))
        self.assertIsNone(validate_claim_form(dict(valid, claim_reason="x" * 2000)))

    def test_login_role_and_csrf(self):
        for path in ("/my-claims", "/found-items/1/claim"):
            self.assertEqual(self.client.get(path).location, "/login")
        self.sign_in()
        for token in (None, "wrong"):
            data = dict(lost_id="1", claim_reason="My item")
            if token is not None:
                data["csrf_token"] = token
            self.assertEqual(self.client.post("/found-items/1/claim", data=data).location, "/")
        self.sign_in(role="admin")
        self.assertEqual(self.client.get("/found-items/1/claim").status_code, 403)
        self.assertEqual(self.client.post("/found-items/1/claim", data={"csrf_token": "test-token"}).status_code, 403)

    def test_outage_and_invalid_found_id(self):
        self.sign_in()
        for path in ("/found-items/0/claim", "/found-items/2147483648/claim"):
            self.assertEqual(self.client.get(path).status_code, 404)
        for method in ("get", "post"):
            response = getattr(self.client, method)(
                "/found-items/1/claim", data={"csrf_token": "test-token", "lost_id": "1", "claim_reason": "My item"},
            )
            self.assertEqual(response.status_code, 503)
            self.assertIn(b"Claims are unavailable", response.data)
            self.assertNotIn(b"Claim submitted successfully", response.data)
        response = self.client.get("/my-claims")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"You have not submitted", response.data)

    def test_form_rendering_and_no_lost_reports(self):
        with app.test_request_context():
            session.update(user_id=1, role="student")
            context = dict(found_item=dict(found_id=4, item_name="Keys", status="Available"),
                           lost_reports=[dict(lost_id=2, item_name="My keys", lost_date=date(2026, 1, 1))],
                           form_data=dict(lost_id="2", claim_reason="<script>private</script>"),
                           error="Try again", database_available=True)
            html = render_template("claim_form.html", **context)
            for value in ('method="post"', 'name="csrf_token"', 'value="2" selected',
                          '/found-items/4/claim', '&lt;script&gt;private&lt;/script&gt;'):
                self.assertIn(value, html)
            context["lost_reports"] = []
            html = render_template("claim_form.html", **context)
            self.assertIn("You need an unresolved lost report", html)
            self.assertNotIn("Submit claim</button>", html)

    def test_claim_link_eligibility_and_no_reason_on_details(self):
        item = dict(found_id=4, user_id=2, item_name="Keys", description="Blue",
                    category_name="Keys", location="Library", item_date=date(2026, 1, 1),
                    status="Available", claim_reason="PRIVATE SENTINEL")
        with app.test_request_context():
            session.update(user_id=1, role="student")
            html = render_template("item_detail.html", item=item, item_type="Found", error=None)
            self.assertIn("/found-items/4/claim", html)
            self.assertNotIn("PRIVATE SENTINEL", html)
            for owner, status, role in ((1, "Available", "student"),
                                        (2, "Returned", "student"), (2, "Available", "admin")):
                session["role"] = role
                html = render_template("item_detail.html", item=dict(item, user_id=owner, status=status),
                                       item_type="Found", error=None)
                self.assertNotIn("Claim this item", html)

    def test_my_claims_links_escaping_and_empty_state(self):
        # Template inputs only; claimant filtering must also be verified on PostgreSQL.
        claim = dict(claim_id=3, lost_id=2, found_id=4, lost_item_name="Keys",
                     found_item_name="Found keys", claim_date=date(2026, 1, 1),
                     status="Pending", claim_reason="<b>My initials</b>")
        with app.test_request_context():
            html = render_template("my_claims.html", claims=[claim], error=None)
            for value in ("/items/Lost/2", "/items/Found/4", "Pending", "2026-01-01", "&lt;b&gt;My initials&lt;/b&gt;"):
                self.assertIn(value, html)
            self.assertIn("You have not submitted any claims", render_template("my_claims.html", claims=[], error=None))


if __name__ == "__main__":
    unittest.main()
