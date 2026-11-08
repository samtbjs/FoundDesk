"""Startup configuration checks; importing the app does not connect to PostgreSQL."""

import os
from pathlib import Path
import secrets
import subprocess
import sys
import unittest


class ConfigurationTests(unittest.TestCase):
    def import_app(self, secret):
        environment = os.environ.copy()
        environment["SECRET_KEY"] = secret
        environment["DATABASE_URL"] = ""
        return subprocess.run(
            [sys.executable, "-c", "import app"],
            cwd=Path(__file__).resolve().parents[1], env=environment,
            capture_output=True, text=True, timeout=15,
        )

    def test_blank_and_example_signing_keys_rejected(self):
        for secret in ("", "   ", "replace_with_a_random_secret_key", " replace_with_a_random_secret_key "):
            with self.subTest(secret=secret):
                result = self.import_app(secret)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Set SECRET_KEY to your own random value", result.stderr)

    def test_random_key_allows_startup_without_database(self):
        self.assertEqual(self.import_app(secrets.token_hex(32)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
