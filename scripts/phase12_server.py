"""Serve the retained isolated Phase 12 DB for browser verification on port 5012."""

import json
import os
from pathlib import Path
import re
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import db  # Loads the existing private .env without printing or changing it.
from psycopg.conninfo import conninfo_to_dict, make_conninfo

metadata = json.loads((ROOT / "docs/evidence/phase12/environment.json").read_text())
name = metadata["test_database"]
if not re.fullmatch(r"founddesk_phase12_[0-9a-f]{10}", name):
    raise RuntimeError("Refusing a non-test database")
settings = conninfo_to_dict(os.environ["DATABASE_URL"])
if settings.get("host") not in ("localhost", "127.0.0.1", "::1"):
    raise RuntimeError("Local PostgreSQL only")
settings["dbname"] = name
os.environ["DATABASE_URL"] = make_conninfo(**settings)
os.environ["SECRET_KEY"] = secrets.token_hex(32)
from app import app

if __name__ == "__main__":
    print("Serving isolated test database on http://127.0.0.1:5012")
    app.run(host="127.0.0.1", port=5012, debug=False, use_reloader=False)
