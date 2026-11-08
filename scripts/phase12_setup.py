"""Inspect local FoundDesk and create a separate real PostgreSQL test database."""

import json
import os
from importlib.metadata import version
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from db import get_connection


def main():
    evidence = ROOT / "docs" / "evidence" / "phase12"
    evidence.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        if connection.info.host not in ("localhost", "127.0.0.1", "::1"):
            raise RuntimeError("This script is restricted to local PostgreSQL.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
            tables = [row["tablename"] for row in cursor.fetchall()]
            # Only initialize an entirely empty public schema; never reset existing data.
            if not tables:
                cursor.execute((ROOT / "database/schema.sql").read_text())
                cursor.execute((ROOT / "database/sample_data.sql").read_text())
                print("Initialized previously empty founddesk database.")
            else:
                print("Existing public tables preserved:", ", ".join(tables))
            cursor.execute("SELECT conrelid::regclass::text AS table_name, contype, pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE connamespace = 'public'::regnamespace ORDER BY conrelid::regclass::text, conname")
            constraints = cursor.fetchall()
            info = dict(host=connection.info.host, port=connection.info.port,
                        database=connection.info.dbname, server_version=connection.info.server_version)
            cursor.execute("SELECT rolcreatedb, rolsuper FROM pg_roles WHERE rolname = current_user")
            privileges = cursor.fetchone()
        # Connection.info.dsn deliberately omits the password; reuse the private input.
        original = conninfo_to_dict(os.environ["DATABASE_URL"])
    if not (privileges["rolcreatedb"] or privileges["rolsuper"]):
        raise RuntimeError("The configured DB role needs CREATEDB to provision the isolated test database.")
    test_database = "founddesk_phase12_" + uuid4().hex[:10]
    with psycopg.connect(make_conninfo(**original), autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_database)))
    test_settings = dict(original, dbname=test_database)
    with psycopg.connect(make_conninfo(**test_settings)) as connection:
        connection.execute((ROOT / "database/schema.sql").read_text())
        connection.execute((ROOT / "database/sample_data.sql").read_text())
    metadata = dict(local_database=info, test_database=test_database,
                    python=sys.version.split()[0], packages={name: version(name) for name in
                    ("Flask", "psycopg", "psycopg-binary", "python-dotenv", "Werkzeug")},
                    existing_constraints=constraints)
    (evidence / "environment.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in metadata.items() if key != "existing_constraints"}, indent=2))
    print("Credential-free environment/constraint evidence saved.")


if __name__ == "__main__":
    main()
