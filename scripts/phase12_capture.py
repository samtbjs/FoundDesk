"""Capture credential-free psql and final-state evidence from the isolated DB."""

from datetime import date
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from db import get_connection
import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

evidence = ROOT / "docs/evidence/phase12"
metadata = json.loads((evidence / "environment.json").read_text())
settings = conninfo_to_dict(os.environ["DATABASE_URL"])
if settings.get("host") not in ("localhost", "127.0.0.1", "::1"):
    raise RuntimeError("Local PostgreSQL only")
name = metadata["test_database"]
if not re.fullmatch(r"founddesk_phase12_[0-9a-f]{10}", name):
    raise RuntimeError("Isolated test database required")
settings["dbname"] = name
column_query = "SELECT table_name,column_name,data_type,character_maximum_length,is_nullable,is_identity,identity_generation,column_default FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position"
with get_connection() as original_connection:
    original_columns = original_connection.execute(column_query).fetchall()
psql = Path("C:/Program Files/PostgreSQL/18/bin/psql.exe")
environment = os.environ.copy()
environment["PGPASSWORD"] = settings.get("password", "")
arguments = [str(psql), "-X", "-h", settings["host"], "-p", settings.get("port", "5432"),
             "-U", settings["user"], "-d", name, "-v", "ON_ERROR_STOP=1", "-f", str(ROOT / "database/queries.sql")]
completed = subprocess.run(arguments, env=environment, capture_output=True, text=True, timeout=30)
(evidence / "psql_queries_output.txt").write_text(completed.stdout + completed.stderr, encoding="utf-8")
if completed.returncode:
    raise RuntimeError("psql SQL demonstrations failed; inspect credential-free output")
with psycopg.connect(make_conninfo(**settings), row_factory=dict_row) as connection:
    test_columns = connection.execute(column_query).fetchall()
    actual_constraints = connection.execute("SELECT conrelid::regclass::text AS table_name,contype,pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE connamespace='public'::regnamespace").fetchall()
    schema_matches = original_columns == test_columns and Counter((r['table_name'],r['contype'],r['definition']) for r in actual_constraints) == Counter((r['table_name'],r['contype'],r['definition']) for r in metadata['existing_constraints'])
    if not schema_matches:
        raise AssertionError("Existing founddesk schema differs from the tested schema")
    (evidence / "columns.json").write_text(json.dumps(test_columns,indent=2),encoding="utf-8")
    totals = connection.execute("SELECT (SELECT COUNT(*) FROM lost_items) AS lost_count, (SELECT COUNT(*) FROM found_items) AS found_count, (SELECT COUNT(*) FROM claims WHERE status='Pending') AS pending_count, (SELECT COUNT(*) FROM found_items WHERE status='Returned') AS returned_count").fetchone()
    claim_counts = connection.execute("SELECT status, COUNT(*) AS count FROM claims GROUP BY status ORDER BY status").fetchall()
    demo = connection.execute("SELECT c.claim_id,c.lost_id,c.found_id,c.status AS claim_status,l.status AS lost_status,f.status AS found_status FROM claims c JOIN users u ON u.user_id=c.claimant_id JOIN lost_items l ON l.lost_id=c.lost_id JOIN found_items f ON f.found_id=c.found_id WHERE u.email=%s", ("demo.owner@phase12.example.test",)).fetchall()
    conflicts = connection.execute("SELECT 'found' AS kind,found_id AS id,COUNT(*) AS count FROM claims WHERE status='Approved' GROUP BY found_id HAVING COUNT(*)>1 UNION ALL SELECT 'lost',lost_id,COUNT(*) FROM claims WHERE status='Approved' GROUP BY lost_id HAVING COUNT(*)>1").fetchall()
    if conflicts:
        raise AssertionError("Contradictory approvals found")
    state = dict(date=str(date.today()), database=name, totals=totals,
                 claim_counts=claim_counts, browser_demo=demo, contradictory_approvals=conflicts,
                 psql_exit_code=completed.returncode, original_schema_matches_test_schema=schema_matches)
(evidence / "final_state.json").write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
print(json.dumps(state, indent=2))
print("psql executed all teaching queries and rollback demos successfully.")
