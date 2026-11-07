"""Checks that do not require PostgreSQL. No database is substituted."""

import os
import secrets
import unittest

os.environ.setdefault("SECRET_KEY", secrets.token_hex(32))

from app import app
from werkzeug.security import check_password_hash, generate_password_hash


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.database_url = os.environ.get("DATABASE_URL")
        # Deliberately test missing configuration, without connecting to a server.
        os.environ["DATABASE_URL"] = ""

    def tearDown(self):
        if self.database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.database_url

    def token(self, path="/register"):
        self.client.get(path)
        with self.client.session_transaction() as current_session:
            return current_session["csrf_token"]

    def registration(self, **changes):
        data = {
            "csrf_token": self.token(),
            "full_name": "Test Student",
            "email": "student@example.com",
            "password": "Temporary-test-password",
            "confirm_password": "Temporary-test-password",
        }
        data.update(changes)
        return self.client.post("/register", data=data)

    def test_forms_and_logged_out_navigation(self):
        for path in ("/register", "/login"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'name="csrf_token"', response.data)
            self.assertIn(b'href="/login"', response.data)
            self.assertIn(b'href="/register"', response.data)
            self.assertNotIn(b'>Logout</button>', response.data)

    def test_registration_validation_and_password_not_redisplayed(self):
        cases = [
            ({"full_name": " "}, b"Enter a full name"),
            ({"email": "invalid"}, b"Enter a valid email"),
            ({"password": "short"}, b"Use a password"),
            ({"confirm_password": "different"}, b"Passwords do not match"),
        ]
        for changes, message in cases:
            with self.subTest(changes=changes):
                response = self.registration(**changes)
                self.assertIn(message, response.data)
                self.assertNotIn(b"Temporary-test-password", response.data)

    def test_csrf_rejects_missing_wrong_and_unicode_tokens(self):
        for path in ("/register", "/login", "/logout"):
            self.token()
            for token in (None, "wrong", "\u2603"):
                data = {} if token is None else {"csrf_token": token}
                response = self.client.post(path, data=data)
                self.assertEqual(response.status_code, 302)
                with self.client.session_transaction() as current_session:
                    self.assertNotIn("user_id", current_session)
                page = self.client.get(response.location)
                self.assertIn(b"Your form expired or was invalid", page.data)

    def test_database_unavailable_does_not_authenticate(self):
        response = self.registration()
        self.assertIn(b"Registration is unavailable", response.data)
        response = self.client.post("/login", data={
            "csrf_token": self.token("/login"),
            "email": "student@example.com",
            "password": "Temporary-test-password",
        })
        self.assertIn(b"Login is unavailable", response.data)
        self.assertNotIn(b"DATABASE_URL is not configured", response.data)
        with self.client.session_transaction() as current_session:
            self.assertNotIn("user_id", current_session)

    def test_logout_requires_login_and_post(self):
        self.assertEqual(self.client.get("/logout").status_code, 405)
        response = self.client.post("/logout", data={"csrf_token": self.token()})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/login")

    def test_logout_clears_authentication_and_csrf(self):
        # Set only a test session; this does not test PostgreSQL login success.
        with self.client.session_transaction() as current_session:
            current_session["user_id"] = 1
            current_session["role"] = "student"
            current_session["csrf_token"] = "test-csrf-token"
        response = self.client.get("/")
        self.assertIn(b'>Logout</button>', response.data)
        self.assertNotIn(b'href="/register"', response.data)
        self.client.post("/logout", data={"csrf_token": "wrong"})
        with self.client.session_transaction() as current_session:
            self.assertEqual(current_session["user_id"], 1)
        response = self.client.post("/logout", data={"csrf_token": "test-csrf-token"})
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as current_session:
            self.assertNotIn("user_id", current_session)
            self.assertNotIn("role", current_session)
            self.assertNotIn("csrf_token", current_session)

    def test_werkzeug_hashes_are_salted_and_verify(self):
        password = "Temporary-test-password"
        first_hash = generate_password_hash(password)
        self.assertNotEqual(first_hash, password)
        self.assertNotEqual(first_hash, generate_password_hash(password))
        self.assertTrue(check_password_hash(first_hash, password))
        self.assertFalse(check_password_hash(first_hash, "wrong-password"))


if __name__ == "__main__":
    unittest.main()
