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
│   └── index.html
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
