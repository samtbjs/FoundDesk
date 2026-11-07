"""Search validation and rendering checks; no database substitutes or SQL execution."""

import os
import secrets
import unittest
from datetime import date

os.environ.setdefault("SECRET_KEY", secrets.token_hex(32))

from flask import render_template
from app import app


class SearchTests(unittest.TestCase):
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

    def sign_in(self):
        with self.client.session_transaction() as current_session:
            current_session["user_id"] = 1

    def test_login_required(self):
        for path in ("/browse-items", "/items/Lost/1", "/items/Found/1"):
            self.assertEqual(self.client.get(path).location, "/login")

    def test_invalid_filters_and_detail_ids(self):
        self.sign_in()
        for query in ({"type": "bad"}, {"category_id": "abc"},
                      {"category_id": "0"}, {"category_id": "2147483648"},
                      {"keyword": "x" * 151}, {"location": "x" * 201}):
            self.assertEqual(self.client.get("/browse-items", query_string=query).status_code, 400)
        for path in ("/items/Other/1", "/items/Lost/0", "/items/Found/2147483648"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_database_unavailable_is_not_empty_results(self):
        self.sign_in()
        response = self.client.get("/browse-items?keyword=Keys")
        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Items are unavailable", response.data)
        self.assertIn(b'value="Keys"', response.data)
        self.assertNotIn(b"No items match", response.data)
        for item_type in ("Lost", "Found"):
            response = self.client.get(f"/items/{item_type}/1")
            self.assertEqual(response.status_code, 503)
            self.assertIn(b"Item details are unavailable", response.data)

    def test_templates_escape_values_and_link_correct_type(self):
        # These are template inputs only, not simulated database results.
        item = dict(item_id=7, item_name="<script>bad</script>",
                    description="<b>Blue</b>", category_name="Keys",
                    location="Library", item_date=date(2026, 1, 1),
                    status="Available", item_type="Found")
        filters = dict(keyword="Keys", category_id="2", location="Library", type="Found")
        with app.test_request_context():
            html = render_template("browse_items.html", filters=filters,
                                   categories=[dict(category_id=2, category_name="Keys")],
                                   items=[item], error=None)
            self.assertIn('href="/items/Found/7"', html)
            self.assertIn('value="2" selected', html)
            self.assertIn('value="Found" selected', html)
            self.assertIn("&lt;script&gt;bad&lt;/script&gt;", html)
            html = render_template("item_detail.html", item=item, item_type="Found", error=None)
            self.assertIn("&lt;b&gt;Blue&lt;/b&gt;", html)
            for value in ("Keys", "Library", "2026-01-01", "Available"):
                self.assertIn(value, html)
            html = render_template("browse_items.html", filters=filters,
                                   categories=[], items=[], error=None)
            self.assertIn("No items match", html)


if __name__ == "__main__":
    unittest.main()
