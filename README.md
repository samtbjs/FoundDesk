# FoundDesk

Lost and Found Item Tracking System — a college DBMS mini project using Python,
Flask, PostgreSQL, psycopg 3, Jinja/HTML and basic CSS.

**Phase 11 status: static review and draft documentation prepared. The project is
not complete. Real PostgreSQL integration, browser checks and screenshots are
pending Phase 12.** No SQLite, ORM, mock database or external service is used.

## Current features

- Registration/login/logout with password hashes and CSRF-protected forms.
- Owned lost/found report creation, editing and deletion when eligible.
- Browse by keyword/item name, category, location and Lost/Found/All; item details.
- Student claims linking an owned unresolved loss to another user's Available find.
- My Claims with private reasons and status.
- Admin Pending Claims dashboard, transactional approval/rejection and Reports.
- SQL examples, database design, draft report, viva guide and explicit test checklist.

Home/register/login are public. Item/report/claim pages require login. Submission
requires student role; admin decisions and Reports require admin role. The server
checks access even when buttons/links are hidden.

## Project files

| Path | Purpose |
| --- | --- |
| app.py | Flask routes, validation, authentication/CSRF, explicit SQL and claim decisions |
| db.py | Load .env and create psycopg dict-row connections with a five-second timeout |
| templates/ | Base layout, account/report/search/claim/admin/Reports pages and shared totals |
| static/css/style.css | Minimal styles |
| database/schema.sql | Five tables, PK/FK/UNIQUE/NOT NULL/CHECK/default constraints |
| database/sample_data.sql | Six categories, no accounts/passwords |
| database/queries.sql | Explained SELECTs and temporary rolled-back view/DML demos |
| tests/ | Non-DB unittest checks, without a substitute database |
| .env.example | Placeholder settings; copy locally and replace values |
| requirements.txt | Flask, psycopg[binary], python-dotenv |
| docs/ | Draft project report, review, design, SQL/viva guides and testing checklist |

## 1. Install Python dependencies (Windows PowerShell)

Open a terminal in the FoundDesk folder. Install Python 3 if needed. For a new
checkout, create the virtual environment; reuse the existing .venv if it works.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Directly invoking the environment's Python avoids an activation-policy requirement.
If `py` is unavailable, use your installed Python executable to create .venv.
Do not overwrite a working environment merely to follow these setup examples.

On macOS/Linux, the equivalent is `python3 -m venv .venv`, then
`.venv/bin/python -m pip install -r requirements.txt`. Use that Python path for
subsequent Flask/test commands.

## 2. Configure local settings

Copy only when .env does not already exist:

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Paste the generated value into SECRET_KEY in your local .env. Never share it.
The application rejects blank/whitespace/the shipped placeholder at startup.
DATABASE_URL should use your actual local credentials after PostgreSQL setup:

```dotenv
FLASK_APP=app
DATABASE_URL=postgresql://your_postgres_user:your_url_encoded_password@localhost:5432/founddesk
SECRET_KEY=your_generated_random_value
```

Percent-encode reserved characters in the URL password. Keep .env out of Git;
.env.example contains placeholders only. Existing process environment values take
precedence over dotenv values; remove stale environment overrides if edits seem
ineffective. Do not paste credentials into documentation, screenshots or issues.

PostgreSQL may be installed later. With a valid secret, Flask can start without a
working DB and shows availability messages; real registration, reporting, claims
and SQL reads cannot succeed until PostgreSQL is configured. Do not substitute
SQLite or remove DB features to get a successful-looking demonstration.

## 3. Initialize PostgreSQL locally (Phase 12)

Install PostgreSQL and optionally pgAdmin. Start the server on localhost:5432.
Create a new `founddesk` database; run the schema once on the new database, then
seed categories. Use your chosen local PostgreSQL role in place of postgres if
needed. Commands prompt for its password; do not place the password in a command.

```powershell
psql -h localhost -p 5432 -U postgres -c "CREATE DATABASE founddesk;"
psql -h localhost -p 5432 -U postgres -d founddesk -v ON_ERROR_STOP=1 -f database/schema.sql
psql -h localhost -p 5432 -U postgres -d founddesk -v ON_ERROR_STOP=1 -f database/sample_data.sql
```

Do not rerun database creation/schema.sql over an initialized database. The seed
script is repeatable. In pgAdmin, select the database, open Tools > Query Tool,
open each SQL file and execute the whole script in order. The schema/seed files
use BEGIN/COMMIT. If a transaction fails, ROLLBACK before retrying. Detailed
instructions are in [Database design](docs/database_design.md).

No default users, admin password or automatic migration is installed. Register an
intended admin normally after starting Flask, then promote that account using
trusted local psql/pgAdmin SQL (replace the email):

```sql
UPDATE users SET role = 'admin' WHERE email = 'your-admin-email@example.com';
```

Log out and back in to load the new role. Roles are cached in signed login sessions;
existing sessions do not immediately reflect database role changes/account deletion.
This local mini project does not implement session revocation.

## 4. Start and use the application

```powershell
.\.venv\Scripts\python.exe -m flask --app app run
```

Open [FoundDesk locally](http://127.0.0.1:5000/). Stop with Ctrl+C. This is the
local Flask development server; no deployment or HTTPS setup is included.

1. Register/log in as students A and B using test data.
2. As A, report a Lost item. As B, report an Available found item.
3. As A, browse/filter, open B's found item and choose Claim this item.
4. Select A's unresolved lost report, enter a reason and submit; inspect My Claims.
5. As admin, open Admin, verify ownership and approve/reject a Pending claim.
6. Inspect item statuses, My Claims and [Reports locally](http://127.0.0.1:5000/reports).

These are intended demonstration steps, **not recorded passing results**. Follow
the testing checklist in Phase 12 and capture only actual screenshots/SQL output.

## Implementation and SQL walkthrough

GET search values flow through request.args, validation, bound psycopg SELECTs,
dictionary rows and Jinja tables. Search matches item_name/location with ILIKE;
`%` and `_` retain wildcard meaning. Categories use JOIN for readable names.
State-changing POST forms include a session CSRF token checked before routes run.

Reporting inserts session ownership and initial status, ignoring forged owner/status
fields. Owner/status predicates protect edits. Deletes require no referencing claim;
FKs also restrict deletion. Claim INSERT uses the session claimant, CURRENT_DATE and
Pending after ownership/availability checks and found-then-lost row locks.

Approval locks found, lost and overlapping claim rows, rechecks eligibility, and
updates selected claim Approved, found Returned, lost Resolved and other Pending
claims sharing either item Rejected in one transaction. Rejection changes only a
Pending claim. Success appears after commit; if a connection is lost during commit,
refresh the dashboard/check the DB before retrying because the outcome may be uncertain.

All user values are bound separately from SQL. Browse concatenates fixed condition
strings only. Reports use independent COUNT subqueries, pre-aggregated LEFT JOINs
for categories and grouped claim statuses. Separate SELECTs can observe different
committed moments during concurrent changes; there is no historical report snapshot.
There is no return-date column: Returned reports display found_date.

The entity tables avoid repeated account/category data. The claims table retains
claimant_id even though owner-only claiming makes it derivable through lost_id;
this is a documented strict 2NF/3NF limitation, not a claim of perfect normalization.

## Verification and remaining work

Run non-DB checks from the project root:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app.py db.py tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests deliberately clear DATABASE_URL, use explicit test sessions and template
inputs, and check validation, access/CSRF, escaping, startup and unavailable-DB paths.
They do not establish successful DB login, SQL syntax/results, persistence,
constraints, transactions, concurrency or browser layout. See the exact recorded
run status in [Testing checklist](docs/testing_checklist.md).
Phase 11 verification on 2026-11-08: compilation, all 42 tests and loading all 14
Jinja templates passed. No successful PostgreSQL operation was tested.

Every end-to-end/DB case is NOT YET RUN until executed with local PostgreSQL.
Phase 12 must verify schema/constraints; real authentication and CRUD; search and
aggregate SQL; multi-account privacy; duplicate/race/rollback behavior; browser
flows; and actual screenshots/results. Apply necessary fixes, rerun affected checks
and finalize the draft report only after that work. Do not declare completion now.

## Documentation

- [Draft project report](docs/project_report.md): all required report sections and screenshot placeholders.
- [Static review](docs/static_review.md): review scope, findings, necessary fix and limitations.
- [Viva guide](docs/viva_guide.md): frontend, Flask, security, database, SQL and request-flow answers.
- [Database design](docs/database_design.md): entities, attributes, ER, relational constraints and normalization caveat.
- [SQL reports guide](docs/sql_reports.md): each query's meaning and pgAdmin steps.
- [Testing checklist](docs/testing_checklist.md): evidence ledger and NOT YET RUN integration cases.

For optional SQL demonstrations after DB initialization:

```powershell
psql -h localhost -p 5432 -U postgres -d founddesk -v ON_ERROR_STOP=1 -f database/queries.sql
```

Q1–Q8 read application data. Execute Q9/Q10 only as complete BEGIN-through-ROLLBACK
blocks. They create temporary objects and never write application rows/sequences.
Flask does not need this script installed; see the SQL guide for interactive use.

## Phase 11 changes and viva

Changed app.py to reject blank/known-example signing keys; added startup regression
tests. Prepared the draft report, review and viva guide; organized current setup;
labelled deferred test cases explicitly. No schema/query migration or DB operation
was performed, and no fabricated evidence is included.

1. **What does static review prove?** It identifies code-level issues and consistency;
   it does not prove successful database or concurrent behavior.
2. **Why reject the example SECRET_KEY?** A known key could allow forged signed
   session contents, including an admin role.
3. **Why is Phase 12 still needed?** Real DB workflows, constraints, races, rollback,
   browser behavior and screenshots need actual execution and recorded evidence.

Suggested commit: `docs: prepare project documentation and testing checklist`.
No automatic commit is part of this phase.
