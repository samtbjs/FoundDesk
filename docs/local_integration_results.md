# Phase 12 local PostgreSQL integration results

Verified on 2026-11-08 on this Windows computer. This was not a cloud-only
simulation: the configured local PostgreSQL connection, real SQL, committed
Flask operations, psql and browser HTTP requests were exercised.

## Environment and data scope

- Windows service `postgresql-x64-18`: Running.
- `pg_isready -h localhost -p 5432`: accepting connections.
- PostgreSQL 18.6; Python 3.14.10; Flask 3.1.3; psycopg/psycopg-binary 3.3.8;
  python-dotenv 1.2.4; Werkzeug 3.1.9. `pip check`: no broken requirements.
- Existing `.env` was valid; it was neither printed nor overwritten. Existing
  `founddesk` tables/data were preserved. No account password or application key
  was changed. No commit was created.
- A fresh **real PostgreSQL database**, `founddesk_phase12_41a2c6ee18`, ran the
  actual schema and seed scripts. Test settings were process-local overrides of
  DATABASE_URL, with a fresh signing key. The app implementation was unchanged.
- Browser verification used `http://127.0.0.1:5012`, served by phase12_server.py
  against that isolated database, not the original founddesk database.

The original and test databases' column definitions and constraints matched in
the final read-only comparison (`original_schema_matches_test_schema: true`).
Raw credential-free metadata and constraints are in
[environment.json](evidence/phase12/environment.json) and
[test_constraints.json](evidence/phase12/test_constraints.json) and
[columns.json](evidence/phase12/columns.json).

## Actual results

| Check | Observed result |
| --- | --- |
| Python compilation | PASS: app.py, db.py, tests and scripts |
| Requirements installation | PASS: pip install --no-index -r requirements.txt found all required packages already satisfied; no upgrade/network fetch needed |
| Existing non-DB suite | PASS: 42 tests |
| Real PostgreSQL suite | PASS: 18 integration tests, 92.406 seconds in this run |
| Schema/seed | Five tables; five PKs, seven FKs, three UNIQUEs, four status/role CHECKs; required-column constraints present. Seed rerun retained six categories before the test-specific category was added. |
| Initial data | users/lost/found/claims all zero in the new DB before account registration. |
| Authentication | Real registrations, hashed password persistence/verification, normalized duplicate email rejection, incorrect password denial, login/logout. Forged admin role at registration ignored. |
| Report CRUD | Real create/edit/delete; owner predicates resisted another student's direct edit/delete; invalid/empty name, bad category, invalid/future dates did not update records. |
| Search/details | Combined case-insensitive name/category/location filtering, Lost/Found selection, date ordering, empty results, SQL-looking keyword, unknown category and missing detail IDs. Stored HTML rendered escaped. |
| Claims/privacy | Actual Pending insertion using session claimant/CURRENT_DATE; duplicate pairs rejected; another claimant/found owner could not read reasons through My Claims; admin could review them. Shared pages omitted reasons. |
| Eligibility/deletion | Own-found/admin submission denied; other-owned/missing/resolved loss and Returned find rejected. Claimed reports survived route deletes; direct DELETE hit the FK RESTRICT constraint. |
| Decisions | Approval updated the selected claim and both items, rejected shared-found/shared-lost competitors, and left unrelated claims eligible. Reject left item statuses unchanged. Repeated decisions returned 409. |
| Atomic rollback | A temporary CHECK failure deliberately blocked the found UPDATE after the claim UPDATE. Route returned 503 and all original states remained; after removing the constraint the approval succeeded. |
| Concurrency | Shared-found and shared-lost approvals gave one 302 and one 409; crossing independent approvals both succeeded and rejected their conflicts. Duplicate submissions and approve/reject race allowed one winner. Submission versus approval left no contradictory Pending competitor. |
| Connectivity failure | Switched the test process to closed loopback port 1, producing real connection failures; relevant pages returned 503 and login showed unavailable. Restoring the URL recovered Reports. The user's PostgreSQL service was not stopped. |
| Aggregates | Dedicated category with two losses/three finds showed 2/3, not 6/6; unused categories remained 0/0. Dashboard totals matched direct COUNTs. |
| SQL examples | All queries and both rolled-back temp-object demos succeeded through psycopg and installed psql. Row counts/production identity values in the test DB stayed unchanged during demo execution; temporary objects disappeared. |
| Browser workflow | Registered two additional students, submitted loss/find, filtered, claimed, approved as admin, rejected a separate claim, viewed Reports and verified Approved/Resolved/Returned. Real screenshots saved. |

Detailed machine-readable records:
[integration_results.json](evidence/phase12/integration_results.json),
[initial_counts.json](evidence/phase12/initial_counts.json),
[query_results.json](evidence/phase12/query_results.json),
[psql_queries_output.txt](evidence/phase12/psql_queries_output.txt),
[final_state.json](evidence/phase12/final_state.json).

## Concrete browser and SQL observations

The browser-created claim **21** links loss **24** and find **23**. It was displayed
as Pending, approved through the admin POST form, then read back as Approved in
My Claims. Both the browser and final SQL show loss 24 Resolved and find 23 Returned.
Claim **6**, a separate test fixture, was rejected through the browser.

At the final snapshot there were **22 lost reports, 22 found reports, 1 Pending
claim and 10 Returned items**. Claim counts were **9 Approved, 1 Pending and
11 Rejected**. No duplicate Approved found IDs or lost IDs were returned by the
invariant queries. These counts are test data, not a seeded production dataset.

Returned count is deliberately not equal to Approved count: eligibility tests
manually changed a found status to exercise stale-state rejection. The reports
correctly count the actual found status, rather than infer it from claims. Early
screenshots show earlier counts because data was created/decided during the run;
they are point-in-time evidence, not a claimed single immutable snapshot.

## Failures investigated and corrections

No application or SQL defect was established in the tested workflows. The first
two runs uncovered harness issues, retained in integration_results_attempt1.json
and integration_results_attempt2.json:

1. The CSRF helper fetched /login without following the authenticated redirect;
   its response was a redirect rather than a token-bearing page. Fixed the helper
   to follow redirects and reran in a fresh DB.
2. A generated category label exceeded VARCHAR(50). Shortened test labels.
3. PostgreSQL 18 reported SQLSTATE 23001 (`RestrictViolation`) for direct deletion
   blocked by ON DELETE RESTRICT. The test expected only 23503 (`ForeignKeyViolation`).
   The test now accepts either appropriate integrity error; the application already
   prevented the route deletion. No weakening of a constraint was needed.
4. Initial setup tried reconnecting with connection.info.dsn, which strips passwords.
   Corrected the setup helper to reuse the existing private environment input.
   No password was displayed and no original-data mutation occurred.

The successful 18-case run used a newly initialized DB. Prior failed runs were not
relabelled as passes. Concurrency cases passed for this bounded run; this is not a
stress/performance certification or proof covering every possible interleaving.

## Screenshots and remaining scope

The [project report](project_report.md) embeds actual screenshots. S10 is represented
by actual psql output/constraint metadata rather than an invented pgAdmin image.
No pgAdmin editor action, exhaustive viewport/accessibility test, account-revocation
feature, live service stop/start, packet loss during commit or prolonged load test
is claimed. Additional unexecuted variants are explicitly listed in
[testing_checklist.md](testing_checklist.md).

The core Phase 12 workflow is verified. Broader checklist variants and user-specific
title-page details remain to be completed before final submission/acceptance.

## Reproduce from PowerShell

From the FoundDesk project root, with the existing private .env configured:

```powershell
Get-Service -Name postgresql-x64-18
& 'C:\Program Files\PostgreSQL\18\bin\pg_isready.exe' -h localhost -p 5432
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h localhost -p 5432 -U your_postgres_user -d founddesk -c 'SELECT version();'
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/phase12_setup.py
.\.venv\Scripts\python.exe tests/postgres_integration.py
.\.venv\Scripts\python.exe scripts/phase12_server.py
```

The setup helper needs CREATEDB or superuser privileges and only initializes the
original schema if it has no public tables at all. Otherwise it preserves them.
Each setup call creates a new isolated database and replaces environment.json with
its name. Do not run it casually after capturing screenshots; archive the evidence
folder first if reproducing. Integration tests refuse a reused nonempty users table
and any non-test database name. Test databases are retained for inspection, not
automatically deleted. Run the ordinary app against .env using `python -m flask
--app app run` on port 5000; the isolated demo server uses port 5012.

The agent-started port-5012 server was stopped after screenshots/evidence were
captured. Restart it with phase12_server.py when inspecting the retained test data.

psql may not be on PATH: the absolute path above was used successfully here.
For pgAdmin access, open the installed pgAdmin 4, connect to localhost:5432 using
your credentials, select the test database, then Tools > Query Tool. Open
database/queries.sql and execute reads individually or complete BEGIN/ROLLBACK
demo blocks. This is a reproduction instruction, not a claim that pgAdmin UI
execution was observed.
