# FoundDesk

Lost and Found Item Tracking System — a college DBMS mini project using Python,
Flask, PostgreSQL, psycopg 3, Jinja/HTML and basic CSS.

**Phase 12 status: the core local PostgreSQL/browser workflow is verified.**
All 42 non-DB tests and 18 real PostgreSQL integration tests passed on 2026-11-08.
Real screenshots and SQL output are included. Extended unexecuted variants and
submission details are listed in the checklist; no blanket acceptance claim is
made for those. No SQLite, ORM, mock database or external service is used.

## Current features

- Registration/login/logout with password hashes and CSRF-protected forms.
- Owned lost/found report creation, editing and deletion when eligible.
- Browse by keyword/item name, category, location and Lost/Found/All; item details.
- Student claims linking an owned unresolved loss to another user's Available find.
- My Claims with private reasons and status.
- Admin Pending Claims dashboard, transactional approval/rejection and Reports.
- SQL examples, database design, evidenced report, viva guide and explicit test checklist.

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
| docs/ | Project report, review, real evidence, design, SQL/viva/demo guides and checklist |
| scripts/phase12_*.py | Isolated real PostgreSQL setup, browser server and evidence capture |
| tests/postgres_integration.py | Explicit real-DB suite, separate from default test discovery |

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

PostgreSQL 18 is now installed and was reached successfully on this computer.
For a new machine where it is not yet installed, Flask can start with a valid secret without a
working DB and shows availability messages; real registration, reporting, claims
and SQL reads cannot succeed until PostgreSQL is configured. Do not substitute
SQLite or remove DB features to get a successful-looking demonstration.

## 3. Initialize PostgreSQL locally

Install PostgreSQL and optionally pgAdmin. Start the server on localhost:5432.
Create a new `founddesk` database; run the schema once on the new database, then
seed categories. Use your chosen local PostgreSQL role in place of postgres if
needed. Commands prompt for its password; do not place the password in a command.

On this machine the service is `postgresql-x64-18` and the executables are under
`C:\Program Files\PostgreSQL\18\bin`. Confirm access in PowerShell:

```powershell
Get-Service -Name postgresql-x64-18
& 'C:\Program Files\PostgreSQL\18\bin\pg_isready.exe' -h localhost -p 5432
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h localhost -p 5432 -U your_postgres_user -d founddesk -c 'SELECT version();'
```

If psql is not on PATH, use that absolute executable path for the commands below.
The existing founddesk schema was already initialized here and was preserved;
skip CREATE DATABASE/schema.sql for that existing database.

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

This sequence was exercised in the browser against an isolated local test DB.
See [actual local results](docs/local_integration_results.md), [real screenshots](docs/project_report.md)
and the [compact demo plus ten viva answers](docs/demo_script.md).

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
Phase 12 reran compilation and all 42 non-DB tests successfully. All 18 additional
real PostgreSQL integration tests passed, including ownership/privacy, duplicate
claims, forced rollback and bounded concurrent decisions/submissions. Actual
psql execution of queries.sql and a browser registration-to-return flow passed.
Installed requirements were already satisfied; pip check found no broken dependencies.

To reproduce in a fresh isolated PostgreSQL test DB (needs CREATEDB privileges):

```powershell
.\.venv\Scripts\python.exe scripts/phase12_setup.py
.\.venv\Scripts\python.exe tests/postgres_integration.py
.\.venv\Scripts\python.exe scripts/phase12_server.py
```

The browser test server uses port 5012; the normal .env app uses port 5000.
Each setup run creates another test database and replaces the metadata file;
archive docs/evidence/phase12 before reproducing if you want to retain this run's
screenshots/results. Original founddesk data is preserved and .env is not rewritten.
The suite refuses to run on a non-test DB or reuse a populated test account table.
SQL/browser evidence is from founddesk_phase12_41a2c6ee18. Failed harness attempts
were retained separately, not passed off as successful runs.

Extended cases still unexecuted include full narrow-viewport/keyboard sweeps,
all validation permutations, registration races, live service stop/start, network
loss during commit, prolonged load and pgAdmin editor execution. See the checklist
for exact scope; title-page details/user acceptance also remain to be supplied.

## Documentation

- [Project report](docs/project_report.md): required sections and real screenshots/output links.
- [Local integration results](docs/local_integration_results.md): versions, actual results, harness corrections and reproduction steps.
- [Compact demo and ten viva questions](docs/demo_script.md).
- [Static review](docs/static_review.md): review scope, findings, necessary fix and limitations.
- [Viva guide](docs/viva_guide.md): frontend, Flask, security, database, SQL and request-flow answers.
- [Database design](docs/database_design.md): entities, attributes, ER, relational constraints and normalization caveat.
- [SQL reports guide](docs/sql_reports.md): each query's meaning and pgAdmin steps.
- [Testing checklist](docs/testing_checklist.md): actual PASS evidence and remaining unexecuted variants.

For optional SQL demonstrations after DB initialization:

```powershell
psql -h localhost -p 5432 -U postgres -d founddesk -v ON_ERROR_STOP=1 -f database/queries.sql
```

Q1–Q8 read application data. Execute Q9/Q10 only as complete BEGIN-through-ROLLBACK
blocks. They create temporary objects and never write application rows/sequences.
Flask does not need this script installed; see the SQL guide for interactive use.

## Phase 12 changes and viva

Added isolated-DB setup/server/capture helpers, 18 real-DB tests and actual evidence.
Updated the report/checklist/README/SQL/viva docs and added local results/demo guides.
No application or schema defect was established in the tested flows; corrections
were confined to the new test harness. Test fixtures used actual INSERT/SELECT/
UPDATE/DELETE and rolled-back demo operations; original application data was preserved.

1. **Why an isolated PostgreSQL DB?** It runs the actual SQL/transactions while
   preserving existing application data; it is not a mock or SQLite substitute.
2. **What did rollback testing establish?** A deliberately failed second approval
   UPDATE left the claim and both items unchanged; removing the constraint allowed success.
3. **What did concurrency testing establish?** The tested shared-item decisions
   allowed one winner and rejected conflicts, without claiming every possible race was tested.

Suggested commit: `test: verify local PostgreSQL integration and finalize docs`.
No automatic commit is part of this phase.
