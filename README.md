# FoundDesk

Lost and Found Item Tracking System — a college DBMS mini project.

## Phase 1: Project setup and basic UI

This phase provides a Flask homepage with plain HTML and minimal CSS. Home is
the only active navigation link. Report Lost, Report Found, Browse Items,
My Reports and Login are non-clickable labels for future phases.

## Project structure

```text
FoundDesk/
├── app.py
├── db.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── login.html
│   ├── lost_item_form.html
│   ├── found_item_form.html
│   └── my_reports.html
├── static/
│   └── css/
│       └── style.css
├── database/
│   ├── .gitkeep
│   ├── schema.sql
│   └── sample_data.sql
├── docs/
│   ├── .gitkeep
│   └── database_design.md
├── requirements.txt
├── tests/
│   ├── test_auth.py
│   ├── test_found_items.py
│   └── test_lost_items.py
├── .env                 # Local only; excluded from Git
├── .env.example
├── .gitignore
└── README.md
```

- `app.py` creates the Flask application. The `/` route calls `index()`, which
  renders `index.html`. Running this file directly starts the development server.
- `db.py` loads local environment settings and creates a fresh psycopg connection
  when requested. Query rows use dictionary keys instead of numeric positions.
- `templates/base.html` defines the shared HTML page, heading, navigation and
  stylesheet link. Its Jinja2 blocks let other templates supply a title and content.
- `templates/index.html` extends `base.html` and supplies the homepage content.
- `static/css/style.css` sets a white background, black text, basic spacing and
  a readable font. Flask serves this file from its built-in static route.
- `database/` contains the Phase 2 PostgreSQL schema and initial category data.
- `docs/database_design.md` explains the tables, relationships, normalization,
  Mermaid ER diagram, pgAdmin setup and verification queries. The empty `.gitkeep` files allow
  Git to track both otherwise empty folders; they have no application behavior.
- `requirements.txt` lists Flask, psycopg's binary distribution and python-dotenv.
  Flask handles requests and templates. psycopg connects to PostgreSQL, and
  python-dotenv loads settings from `.env`.
- `.env.example` shows the required settings using placeholders. `.env` holds
  your local database URL and secret key and must not be committed.
- `.gitignore` excludes virtual environments, generated Python files and local
  environment files containing potential secrets.
- `README.md` explains setup, the code and manual testing.

## Setup and run

Install Python 3 first. Open a terminal in this `FoundDesk` directory.

On macOS or Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app app run
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app app run
```

Open http://127.0.0.1:5000 in your browser. Stop the server with `Ctrl+C`.
With the virtual environment active, `python app.py` also starts the app.
The Flask development server is intended for local development. See Phase 3 below
to configure `.env`. Without a working database, the homepage still loads but
displays an item-count availability message.

## Test Phase 1

With the server running:

1. Open the homepage and check its heading, subtitle, navigation and welcome text.
2. Click Home and confirm it returns to the homepage.
3. Confirm all other navigation entries are plain text, with no clickable links.
4. Confirm the page has a white background, black text and a horizontal line.

From a second terminal, check the homepage and stylesheet responses:

```sh
curl -i http://127.0.0.1:5000/
curl -i http://127.0.0.1:5000/static/css/style.css
```

Both should return `200 OK`.

## Database operations

No database operations take place in Phase 1. There are no connections, tables,
SQL queries or stored user details. PostgreSQL does not need to be installed or
running yet. psycopg is listed only as a required project dependency.

## Phase 2: Database design and schema

The database design now includes `users`, `categories`, `lost_items`,
`found_items` and `claims`. Identity primary keys, foreign keys, required columns,
unique constraints and role/status checks maintain relational integrity.
Duplicate claims for the same lost/found pair are rejected. Restricted deletes
protect referenced records from automatic removal.

To install the database separately from Flask, create a PostgreSQL database named
`founddesk` in pgAdmin. Select it, open **Tools > Query Tool**, and run
`database/schema.sql` once in the empty database. Then run
`database/sample_data.sql` to insert the six categories. Use **Open File** and
**Execute script** for each complete script. The seed script can be rerun safely.

See [Database design](docs/database_design.md) for full instructions, SQL
verification queries, an ER diagram, attribute descriptions and Phase 2 viva
questions. No sample users or passwords are included. Phase 2 added SQL files;
Phase 3 below adds the Flask connection code.

## Phase 3: Flask and PostgreSQL connection

### Local configuration

The local `.env` file contains `DATABASE_URL` and a generated `SECRET_KEY`.
The URL currently contains placeholder database credentials because PostgreSQL
will be installed later. The secret key is a random Flask signing secret, separate
from the database password; no login/session features are added in this phase.
Keep `.env` private. `.gitignore` already excludes it while allowing `.env.example`.

For a new checkout, copy `.env.example` to `.env` **only if `.env` does not already
exist**. On macOS/Linux, from the FoundDesk folder:

```sh
cp -n .env.example .env
source .venv/bin/activate
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the generated value into `SECRET_KEY` in `.env`. In PowerShell, use
`if (!(Test-Path .env)) { Copy-Item .env.example .env }` and activate the virtual
environment using the Windows command above.

Once PostgreSQL is installed, replace the URL placeholders in `.env`:

```dotenv
DATABASE_URL=postgresql://your_postgres_user:your_url_encoded_password@localhost:5432/founddesk
SECRET_KEY=your_generated_random_value
```

Use your PostgreSQL role and password. If the password contains URL-reserved
characters, percent-encode them (for example, `@` becomes `%40` and `#` becomes
`%23`). Do not share the completed URL. Existing operating-system environment
variables take precedence over `.env`; restart Flask after editing settings.

### PostgreSQL setup after installation

1. Start PostgreSQL, listening locally on port `5432`.
2. Create `founddesk` using pgAdmin, then execute `database/schema.sql` once
   in that empty database, followed by `database/sample_data.sql`. Full pgAdmin
   instructions are in [Database design](docs/database_design.md).
3. Update `.env` with the matching credentials and database name.

Alternatively, if PostgreSQL's command-line tools are available, these commands
create and initialize a new database. Replace `your_postgres_user` with your
local role, which needs permission to create a database. Enter its password at
the prompt if requested. Skip `createdb` and the schema script if already installed.

```sh
createdb -h localhost -p 5432 -U your_postgres_user founddesk
psql -h localhost -p 5432 -U your_postgres_user -d founddesk -v ON_ERROR_STOP=1 -f database/schema.sql
psql -h localhost -p 5432 -U your_postgres_user -d founddesk -v ON_ERROR_STOP=1 -f database/sample_data.sql
```

### How the homepage gets its counts

1. Importing `db.py` loads the project's `.env` with python-dotenv. Flask reads
   `SECRET_KEY` into its configuration.
2. A request to `/` calls `index()`, which calls `get_connection()`.
3. `psycopg.connect()` reads `DATABASE_URL` and opens a PostgreSQL connection.
   A five-second connection timeout prevents an indefinitely stalled connection
   attempt; it is not a SQL query timeout.
4. A cursor sends a SELECT with two scalar subqueries. Each `COUNT(*)` counts all
   rows in its report table, including resolved or returned reports. No rows are
   inserted, changed or deleted.
5. `fetchone()` returns one dictionary with `lost_count` and `found_count` keys
   because the connection uses `dict_row`. Two subqueries count the tables
   independently, avoiding multiplication of rows from a JOIN.
6. Flask passes that dictionary as `counts` to `index.html`. Jinja2 renders
   `counts.lost_count` and `counts.found_count` in the HTML response.

The SQL is fixed and takes no user input, so it needs no query parameters.
Future queries taking user input must use psycopg placeholders and separate
parameter values, never string interpolation.

The nested `with` blocks close the cursor and connection, including when a query
fails. psycopg commits an open transaction on successful connection-context exit
and rolls it back on error. No permanent global database connection is stored.
See [psycopg's context manager documentation](https://www.psycopg.org/psycopg3/docs/basic/usage.html).

If configuration, connectivity or the query fails with a psycopg error, the page
shows a fixed message suggesting checks for the server, `.env` and schema. It
does not display the exception or connection URL. Counts are unavailable on
failure, rather than showing misleading zeroes. The homepage remains HTTP 200
so its welcome text and navigation remain usable; this is not a health endpoint.

### Exact connection and homepage test commands

From the FoundDesk folder with the virtual environment activated:

```sh
python -m pip install -r requirements.txt
python -m compileall -q app.py db.py
git check-ignore .env
python -c "
from db import get_connection
with get_connection() as connection:
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1 AS connection_ok')
        print(cursor.fetchone())
"
python -m flask --app app run
```

The direct connection command should print `{'connection_ok': 1}` **only after
PostgreSQL is running and `.env` is correct**. On failure this developer-only
command can print a traceback; do not share it without checking for private data.

From a second terminal:

```sh
curl -i http://127.0.0.1:5000/
curl -i http://127.0.0.1:5000/static/css/style.css
```

Open the homepage in a browser too. A newly initialized database has no reports,
so both counts should be `0`. Compare with this SQL in pgAdmin:

```sql
SELECT
    (SELECT COUNT(*) FROM lost_items) AS lost_count,
    (SELECT COUNT(*) FROM found_items) AS found_count;
```

Before installing PostgreSQL, the expected homepage result is the availability
message, with the existing welcome text and navigation still present. Later,
check this error behavior again by stopping your local server and refreshing,
then restarting it and confirming the counts return.

### Verification status and deferred checks

PostgreSQL is not installed locally. Successful database connectivity, SQL
execution, returned count values, and real connection/transaction cleanup have
**not** been verified against PostgreSQL. Run the commands above after installation
and include them in the complete integration testing after Phase 11. A rendered
error page or Python syntax check does not verify database queries.

### Phase 3 viva questions

1. **What does psycopg do?** It opens PostgreSQL connections, sends SQL queries
   and returns their results to Python.
2. **Why use `dict_row`?** It lets Python and Jinja2 access results by meaningful
   column names such as `lost_count` instead of tuple positions.
3. **Why use `with` for connections?** It closes resources automatically and
   commits or rolls back the transaction as appropriate.

### Phase 3 suggested commit message

```text
feat: connect Flask to PostgreSQL and display item counts
```

## Phase 4: User authentication

### Files and behavior

`app.py` now has `/register` and `/login` routes: GET displays a form, and POST
processes it. `/logout` accepts only POST and requires a logged-in session.
`templates/register.html` and `templates/login.html` extend the existing base
template. `base.html` displays flashed messages and shows Login/Register links
for visitors or a Logout form for signed-in users. Future feature labels stay
inactive. The only CSS addition keeps the Logout form inline with navigation.
`tests/test_auth.py` uses the standard-library unittest runner; no new dependencies
or schema changes are needed. Werkzeug is already installed as a Flask dependency.

Registration trims names, trims and lowercases emails, checks field lengths and
a basic email pattern, and requires matching passwords of 8 to 128 characters.
The password itself is not trimmed. HTML form checks help users, but server-side
checks enforce these rules even if browser validation is bypassed. Password
inputs are never filled back into a rendered form or stored in the session.

### Password hashing and SQL operations

`generate_password_hash()` produces a salted password hash using Werkzeug's
default algorithm. `check_password_hash()` checks a submitted password against
that stored hash. Hashing is one-way, so the application never needs to decrypt
or store a plaintext password. Separate registrations with the same password
receive different salted hashes.

Registration first checks whether the normalized email exists:

```sql
SELECT user_id FROM users WHERE email = %s;
```

If it is unused, registration stores the name, email and generated hash:

```sql
INSERT INTO users (full_name, email, password_hash, role)
VALUES (%s, %s, %s, 'student');
```

The role is fixed in SQL. There is no role field in the registration form, and
submitting an extra `role=admin` field cannot change it. The database's UNIQUE
email constraint is the final safeguard, including simultaneous registrations;
the route catches `UniqueViolation` and displays a duplicate-email message.

Login retrieves the account using this query:

```sql
SELECT user_id, password_hash, role FROM users WHERE email = %s;
```

The submitted password is verified in Python. Missing accounts and incorrect
passwords receive the same message. The `%s` placeholders above are psycopg
parameters, with values supplied as a separate tuple to `execute()`; they are
not Python string formatting. Connection context managers commit a successful
registration, roll back a failed operation and close the connection. Logout
does not query or delete database records.

### Sessions, route protection and CSRF

After successful login, `session.clear()` removes the old session state. The
route then stores `user_id` and `role` from the database. Flask stores its default
session in a signed browser cookie: the signature prevents undetected changes,
but the contents are not encrypted. Never store passwords, hashes or database
credentials there. Keep the generated `.env` SECRET_KEY private and stable;
startup now gives a clear error if it is missing. Cookies use HttpOnly and
SameSite=Lax. Local development continues to use HTTP on localhost.

The small `login_required` decorator checks for `user_id` and redirects anonymous
visitors to Login with a flash message. It currently protects Logout and can be
applied to report routes when those phases are requested. It checks login, not
administrator privileges. No report routes or administrator features are added.

`csrf_token()` generates a random token and stores it in the session. Every
state-changing form includes it as a hidden field. A `before_request` function
checks POST, PUT, PATCH and DELETE requests before their route runs, comparing
the submitted and session tokens with a constant-time comparison. Invalid or
missing tokens redirect to Home with a flash message and do not run the action.
Login, registration and logout are all covered. Successful login clears the old
token; the next rendered form generates a new one. Logout clears authentication
and the token, then flashes a confirmation. A later form gets a fresh token.

Use the browser forms when testing: a bare POST from curl has no session token
and is deliberately rejected. Logging out in one tab also invalidates old form
tokens in other tabs, so reopen a form if it reports an expired token.

### Promote a test account manually after installing PostgreSQL

First register the test account through the website. In pgAdmin's Query Tool
connected to `founddesk`, replace the example email below with its normalized
email. This is an intentional administrator action, not public registration:

```sql
UPDATE users
SET role = 'admin'
WHERE email = 'your-test-account@example.com'
RETURNING user_id, email, role;
```

Expect exactly one returned row. Commit if pgAdmin autocommit is disabled.
Log out and log in again so the session reads the updated role. Existing sessions
hold a snapshot of the role from login; this phase does not refresh roles on
every request. To undo the promotion, run the same UPDATE with `role = 'student'`
and log in again. No admin registration endpoint is provided.

### Run and test Phase 4

From the FoundDesk folder, using the existing `.env` and virtual environment:

```sh
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q app.py db.py tests/test_auth.py
python -m unittest discover -s tests -v
python -m flask --app app run
```

For Windows, use `.venv\Scripts\Activate.ps1` instead of the source command.
Open http://127.0.0.1:5000/register or http://127.0.0.1:5000/login.

The automated checks cover form rendering, validation, missing/invalid CSRF,
missing database configuration, password hashing and logout session handling.
They do not substitute a mock database or test database writes. The logout test
creates a signed test-client session directly; it does not verify login credentials.

**PostgreSQL-dependent behavior remains unverified.** After installation and
schema setup (and during the full integration testing after Phase 11), check:

1. Register a test student and confirm success redirects to Login. Query
   `SELECT user_id, full_name, email, role FROM users;` in pgAdmin and confirm
   the normalized email and `student` role. Privately inspect `password_hash`
   to confirm it is a Werkzeug hash rather than the entered password.
2. Repeat registration with that email, including mixed case and surrounding
   spaces submitted directly; confirm there is only one user and a clear error.
3. Log in with the wrong password and an unknown email; both should fail with
   the same message. Correct credentials should redirect Home and show Logout.
4. Log out and confirm Login/Register return. GET `/logout` must return 405.
   Try POST without a token and confirm it cannot log an authenticated user out.
5. Submit a registration with an extra `role=admin` field using browser developer
   tools; the stored role must still be `student`.
6. Promote your test account with the SQL above, then log out/in and confirm
   the stored session role is refreshed. There is no admin-only UI yet.
7. Confirm the homepage still shows real lost/found counts, and that unavailable
   database errors do not expose credentials.

### Phase 4 viva questions

1. **Why hash passwords?** A hash allows verification without storing the original
   password; salts prevent identical passwords from producing identical hashes.
2. **What is a session?** It preserves login state between requests; Flask signs
   the session cookie using SECRET_KEY to detect tampering.
3. **Why use CSRF tokens with POST?** POST alone cannot prove a form originated
   from the application. A token tied to the session is checked before changes.

### Authentication references

- [Flask authentication tutorial](https://flask.palletsprojects.com/en/stable/tutorial/views/)
- [Werkzeug password hashing](https://werkzeug.palletsprojects.com/en/stable/utils/)
- [Flask security considerations](https://flask.palletsprojects.com/en/stable/web-security/)

### Phase 4 suggested commit message

```text
feat: add user authentication with sessions and CSRF protection
```

## Phase 5: Lost item management

### Files and routes

`app.py` adds lost-report validation and four route patterns. All require login,
and POST requests also pass the existing session-based CSRF check. No new
dependencies or schema changes are required. Found-item and claim features
are not implemented; the existing claims table is read only to protect deletion.

| Route | Methods | Purpose and SQL operations |
| --- | --- | --- |
| `/report-lost` | GET, POST | SELECT categories for the dropdown. Validate POST data and INSERT a report using the session user ID and fixed `Lost` status. |
| `/my-reports` | GET | SELECT only the session user's lost reports, JOIN categories for names, and use EXISTS to indicate whether a claim references each report. |
| `/lost-items/<lost_id>/edit` | GET, POST | SELECT the user's unresolved report to fill the form, then UPDATE its five editable fields. Both queries require matching report ID, session user ID and `Lost` status. |
| `/lost-items/<lost_id>/delete` | POST | DELETE only a report owned by the session user with no referencing claim. RETURNING identifies whether a row was deleted. |

`report_lost()` handles both the creation and edit URLs to reuse their fields,
validation and category lookup. `lost_id=None` means creation; a supplied report
ID means editing. The form never asks for a user ID or status: those values are
controlled by the server. Administrators also follow the ownership checks here.
There is no route to change report status in this phase.

`templates/lost_item_form.html` extends the base layout and contains Item Name,
Category, Description, Location Lost and Date Lost. Categories come exclusively
from PostgreSQL. Posted values remain in the form after a validation error.
The submit button is disabled if the database cannot be loaded or there are no
categories; an empty category table produces an instruction to run the seed script.

`templates/my_reports.html` displays reports in a plain table, newest loss date
first. Edit links appear only for `Lost` rows; Delete is a separate POST form
with a hidden CSRF token and appears only for rows without claims. The server
enforces these restrictions even if someone submits a manually constructed URL
or form. Jinja2 escapes user-entered content when rendering it.

`templates/base.html` now links Report Lost and My Reports. Report Found and Browse
Items remain labels. `static/css/style.css` adds only table borders and cell spacing.
`tests/test_lost_items.py` adds checks that do not require PostgreSQL.

### Validation and SQL details

All five fields are required. The route strips surrounding whitespace and the
validator checks item names up to 150 characters, locations up to 200 characters,
a positive PostgreSQL INTEGER category ID, and a real YYYY-MM-DD date no later
than today. The selected ID must also be in the categories retrieved from the
database. The browser's required fields and maximum date assist users; Python
validates submissions again.

The INSERT uses separate psycopg parameters and never trusts a submitted user ID:

```sql
INSERT INTO lost_items
    (category_id, item_name, description, location, lost_date, user_id, status)
VALUES (%s, %s, %s, %s, %s, %s, 'Lost');
```

The edit SELECT and UPDATE both include `lost_id = %s AND user_id = %s AND
status = 'Lost'`. The UPDATE checks these conditions again in case the report
changed after it was selected. It does not change ownership or status.

```sql
UPDATE lost_items
SET category_id = %s, item_name = %s, description = %s,
    location = %s, lost_date = %s
WHERE lost_id = %s AND user_id = %s AND status = 'Lost'
RETURNING lost_id;
```

Deletion combines ownership and claim checks in one statement:

```sql
DELETE FROM lost_items
WHERE lost_id = %s AND user_id = %s
  AND NOT EXISTS (
      SELECT 1 FROM claims WHERE claims.lost_id = lost_items.lost_id
  )
RETURNING lost_id;
```

Any referencing claim blocks deletion, regardless of claim status. A resolved
report may be deleted if it belongs to the user and has no claims; only editing
requires unresolved status. The schema's ON DELETE RESTRICT foreign key is an
additional safeguard, including a claim inserted concurrently. A foreign-key
violation is caught and reported without exposing internal errors. No claims
are deleted automatically.

Successful writes commit when the connection context exits; exceptions roll
them back. Success messages appear only after that exit. The routes redirect to
My Reports after a successful POST, reducing accidental resubmission on refresh.
A database failure shows an availability message rather than claiming there are
no reports or that a write succeeded.

### Run and test Phase 5

From the FoundDesk directory on macOS/Linux:

```sh
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q app.py db.py tests
python -m unittest discover -s tests -v
python -m flask --app app run
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.
Open http://127.0.0.1:5000/report-lost or http://127.0.0.1:5000/my-reports.
Anonymous visitors should be redirected to Login. With PostgreSQL unavailable,
real registration/login cannot complete; database integration remains in place.

The automated checks cover validation, dates, authentication redirects, CSRF
rejection, unavailable database configuration, table action visibility and HTML
escaping. They use test sessions and direct template input for those checks,
without a mock or alternative database.

**PostgreSQL-dependent operations remain unverified.** After installing PostgreSQL
and initializing it using the earlier instructions, test the following (including
during the full integration testing after Phase 11):

1. Register and log in as student A. Confirm the category dropdown shows the
   six seeded names. Submit a lost item and confirm it appears in My Reports.
2. In pgAdmin run the query below and confirm ownership, category, date and
   `Lost` status. Try submitting extra user_id/status fields from browser tools;
   the server must still use student A's ID and `Lost` status.
3. Edit the report and confirm the values persist and the homepage count does
   not increase. Missing/whitespace-only fields, unknown categories, invalid
   dates and future dates must be rejected. Use developer tools to bypass HTML
   validation when testing server validation.
4. Register student B. Their table must not show A's report. While logged in as
   B, try A's edit URL and submit edit/delete forms targeting A's report with B's
   valid session CSRF token. A's row must stay unchanged.
5. Set a test report's status to `Resolved` manually in pgAdmin. Confirm Edit
   disappears and a direct edit request cannot change it. Deletion remains
   allowed if there are no claims.
6. Delete a report without claims and confirm it disappears and the homepage
   lost count decreases. Refresh My Reports and confirm no duplicate action.
7. Verify deletion is blocked for a report with a referencing claim, including
   approved/rejected claims. Because this phase adds no claim or found-item
   workflow, defer creating that fixture through the UI until those phases.
   Confirm the database foreign key also rejects direct deletion of that report.
8. Repeat requests with missing/wrong CSRF tokens and confirm no write happens.
   Confirm database outages produce useful errors without leaking credentials.

```sql
SELECT l.lost_id, l.user_id, l.item_name, c.category_name,
       l.description, l.location, l.lost_date, l.status
FROM lost_items AS l
JOIN categories AS c ON c.category_id = l.category_id
ORDER BY l.lost_id;
```

### Phase 5 viva questions

1. **Why use the session user ID?** It identifies the authenticated user without
   trusting an editable form field for ownership.
2. **How is unauthorized editing prevented?** Both the SELECT and UPDATE filter
   by report ID, owner ID and unresolved status.
3. **Why check claims before deletion?** Deleting a referenced report would break
   the claim's relationship. NOT EXISTS and the foreign key protect it.

### Phase 5 suggested commit message

```text
feat: add lost item reporting and owner-managed reports
```

## Phase 6: Found item management

### Changes and routes

Found-item reporting follows the lost-item module's simple forms, sessions,
CSRF protection, flash messages and connection context managers. No schema or
dependency changes are needed. The claim approval workflow is not implemented.

| Route | Methods | Behavior |
| --- | --- | --- |
| `/report-found` | GET, POST | Loads categories from PostgreSQL; validates and inserts a found report. |
| `/found-items/<found_id>/edit` | GET, POST | Loads and updates only the logged-in user's `Available` report. |
| `/found-items/<found_id>/delete` | POST | Deletes only the logged-in user's report when no claim references it. |
| `/my-reports` | GET | Now loads both lost and found reports, filtered by the session user ID, into separate tables. |

`app.py` adds `report_found()` and `delete_found_item()`, extends `my_reports()`,
and shares `validate_item_report(form_data, date_field)` between lost and found
reporting. The date field argument selects `lost_date` or `found_date`; the
remaining field checks are identical. Routes strip surrounding whitespace,
require all fields, enforce item/location lengths, reject invalid/future dates,
and verify the category against the database's category list.

`templates/found_item_form.html` extends `base.html` and reuses the existing
styling. Its five fields are Item Name, Category, Description, Location Found
and Date Found. The same form handles creation and editing, retains posted
values on errors, and includes a hidden CSRF token. The category list is never
hardcoded. The submit button is disabled when categories/database are unavailable.

`templates/base.html` activates Report Found. `templates/my_reports.html` adds
the found table with edit links for Available rows and CSRF-protected delete
forms for rows without claims. `tests/test_found_items.py` adds checks without
a database. Existing lost tests were updated to call the shared validator.

### Database operations

Creation uses this parameterized statement. The session supplies user_id and SQL
fixes the initial status, so submitted ownership/status fields cannot override them:

```sql
INSERT INTO found_items
    (category_id, item_name, description, location, found_date, user_id, status)
VALUES (%s, %s, %s, %s, %s, %s, 'Available');
```

The edit SELECT requires `found_id = %s AND user_id = %s AND status = 'Available'`.
The UPDATE checks the same conditions again and modifies only the five form fields:

```sql
UPDATE found_items
SET category_id = %s, item_name = %s, description = %s,
    location = %s, found_date = %s
WHERE found_id = %s AND user_id = %s AND status = 'Available'
RETURNING found_id;
```

My Reports SELECTs only the logged-in user's found rows, JOINs categories for
names, and uses EXISTS against claims to determine delete-button visibility.
These are separate queries from lost reports so the two sets do not multiply
each other through a JOIN.

```sql
DELETE FROM found_items
WHERE found_id = %s AND user_id = %s
  AND NOT EXISTS (
      SELECT 1 FROM claims WHERE claims.found_id = found_items.found_id
  )
RETURNING found_id;
```

Any claim status blocks deletion. The existing ON DELETE RESTRICT foreign key
also protects concurrent claim insertion; a foreign-key error produces a clear
message and rollback. A Returned report cannot be edited, but it may be deleted
by its owner if it has no claims. Admin users follow the same ownership rules.
No report status-changing route is added. Success messages follow the committed
write, and database errors never display credentials or fake successful results.

### Lost and found table comparison

Both tables have identity primary keys, required report fields, user/category
foreign keys, and constrained statuses. Both describe one report per row,
reference shared account/category information and are referenced by claims.

| Detail | lost_items | found_items |
| --- | --- | --- |
| Primary key | lost_id | found_id |
| Reporter | Person reporting the loss | Person reporting the discovery |
| Event date | lost_date | found_date |
| Location meaning | Where it was lost/last seen | Where it was found |
| Initial/editable status | Lost | Available |
| Other status | Resolved | Returned |
| Claim foreign key | claims.lost_id | claims.found_id |

They represent independent events: a found report can exist without a matching
lost report and vice versa. A future claim can link the two without duplicating
either report's details.

### Run, tests and deferred PostgreSQL verification

From the FoundDesk folder on macOS/Linux:

```sh
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q app.py db.py tests
python -m unittest discover -s tests -v
python -m flask --app app run
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.
Open http://127.0.0.1:5000/report-found or http://127.0.0.1:5000/my-reports.
The automated tests cover shared/found date validation, login protection, CSRF,
database-unavailable handling, form rendering, action visibility and escaping.
Test sessions and template fixtures do not verify database authentication or SQL.

**Successful PostgreSQL operations remain unverified.** After PostgreSQL setup,
and as part of complete testing after Phase 11:

1. Log in as student A, submit a found item, and verify it appears alongside
   their lost reports in My Reports. Confirm the homepage found count increases.
2. Run the SELECT below in pgAdmin. Confirm A's user ID, the selected category,
   found date and Available status. Manually submit extra user_id/status fields
   and confirm they are ignored by the INSERT.
3. Edit the report and verify all five fields persist. Test empty/whitespace
   fields, oversized names/locations, unknown categories and invalid/future dates
   while bypassing browser validation to exercise Python checks.
4. Log in as B. A's report must be absent from B's table. Direct edit and delete
   requests using A's report ID with B's valid CSRF token must leave it unchanged.
5. Set a test report to Returned in pgAdmin. Direct edit GET/POST requests must
   fail even if an old form was open. Deletion is allowed only if no claims exist.
6. Delete an unclaimed report and verify the row and homepage count update.
   When the claim phase exists, verify any referencing claim blocks deletion
   regardless of its status; do not add a claim workflow early for this test.
7. Repeat lost-item reporting/edit/delete checks to confirm existing behavior.
   Confirm missing/invalid CSRF tokens cannot write data and outages do not
   expose credentials or claim successful changes.

```sql
SELECT f.found_id, f.user_id, f.item_name, c.category_name,
       f.description, f.location, f.found_date, f.status
FROM found_items AS f
JOIN categories AS c ON c.category_id = f.category_id
ORDER BY f.found_id;
```

### Phase 6 viva questions

1. **Why share categories between both report tables?** Each category is stored
   once, preventing inconsistent repeated category names.
2. **How is found-item ownership enforced?** SELECT, UPDATE and DELETE filter
   using the authenticated user's session ID, not a submitted user ID.
3. **What differs between lost and found reports?** They describe different events
   and have different primary keys, event dates and permitted statuses.

### Phase 6 suggested commit message

```text
feat: add found item reporting and management
```

## Phase 7: Search and filtering

Browse Items now links to `/browse-items`. Browsing and `/items/<item_type>/<item_id>`
details require login, like the report pages. Any logged-in student can read reports
from either type; these pages expose no reporter account data or modification forms.
No schema changes, writes, matching libraries or claim workflow were added.

### Files and code walkthrough

- `app.py`: `browse_items()` reads and trims GET values, validates type/length/category
  range, loads categories and checks category membership. It builds a WHERE clause
  using fixed conditions and binds user values separately. Lost and found SELECTs
  run only for the chosen type. The combined list is sorted by event date, ID and
  type descending. `item_detail()` selects one report from a fixed type-specific
  query by bound ID. Missing reports give 404, invalid filters give 400, outages 503.
- `templates/base.html`: enables the Browse Items navigation link.
- `templates/browse_items.html`: GET search row with preserved values, readable
  results table, type-specific detail links, clear link and empty-results message.
- `templates/item_detail.html`: displays the six required fields with Jinja escaping.
- `static/css/style.css`: minimal wrapping search row and multiline descriptions.
- `tests/test_search.py`: login, input validation, unavailable-database responses,
  template escaping, links, selections and empty-results checks without DB substitutes.
- `docs/testing_checklist.md`: tracks unverified PostgreSQL checks for Phase 12.

### GET values to SQL to HTML

For example, `/browse-items?keyword=keys&category_id=2&location=library&type=Found`
becomes `request.args` in Flask. Category 2 must exist. The found query is:

```sql
SELECT i.found_id AS item_id, i.item_name, c.category_name,
       i.location, i.found_date AS item_date, i.status, 'Found' AS item_type
FROM found_items AS i
JOIN categories AS c ON c.category_id = i.category_id
WHERE i.item_name ILIKE %s AND i.category_id = %s AND i.location ILIKE %s
ORDER BY i.found_date DESC, i.found_id DESC;
```

The separate bound values are `('%keys%', 2, '%library%')`. Unselected filters
omit their fixed condition. All filters combine with AND; keyword matches item
name only. `%` and `_` keep SQL wildcard semantics. Lost searches use the analogous
fixed query over `lost_items` and `lost_date`. All runs both SELECTs and merges their
rows in Python. JOIN retrieves category names without duplicating category data.
Details use `WHERE i.lost_id = %s` or `WHERE i.found_id = %s`. Categories use
`SELECT category_id, category_name FROM categories ORDER BY category_name`.
All Phase 7 DB operations are SELECTs. Jinja receives dictionaries and renders
escaped values into the form, table and detail page.

### Run and test (Windows PowerShell)

From the project root, with `.env` configured using `.env.example`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m compileall -q app.py db.py tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m flask --app app run
```

Open `http://127.0.0.1:5000/browse-items`, log in, search and open a result.
The automated tests do not verify SQL execution or successful database reads.
Phase 7 verification: Python compilation and all 23 unittest checks passed.
PostgreSQL integration remains unverified; follow `docs/testing_checklist.md`
after PostgreSQL installation during Phase 12.

### Phase 7 viva questions

1. **Why GET for search?** It reads data without changing it and keeps filters
   in the URL so searches can be bookmarked.
2. **Why ILIKE and bound parameters?** ILIKE supports case-insensitive pattern
   matching; parameters keep input separate from SQL syntax.
3. **Why JOIN categories?** Reports store category foreign keys; JOIN retrieves
   readable names from the shared category table.

Suggested commit: `feat: implement item search and filtering` (do not auto-commit).

## Viva questions

1. **What does a Flask route do?** It maps a URL to a Python function that returns
   a response. Here, `/` maps to `index()`.
2. **What is Jinja2 template inheritance?** A child template extends a shared base
   template and fills its blocks, avoiding repeated HTML.
3. **Why use a virtual environment?** It keeps this project's Python dependencies
   separate from other projects and the system Python installation.

## Suggested commit message

```text
feat: initialize FoundDesk Flask project with basic homepage
```
