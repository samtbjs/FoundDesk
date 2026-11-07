# FoundDesk

Lost and Found Item Tracking System — a college DBMS mini project.

## Phase 1: Project setup and basic UI

This phase provides a Flask homepage with plain HTML and minimal CSS. Home is
the only active navigation link. Report Lost, Report Found, Browse Items,
My Reports and Login are non-clickable labels for future phases.

## Project structure

```text
lostandFound/
├── app.py
├── templates/
│   ├── base.html
│   └── index.html
├── static/
│   └── css/
│       └── style.css
├── database/
│   └── .gitkeep
├── docs/
│   └── .gitkeep
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

- `app.py` creates the Flask application. The `/` route calls `index()`, which
  renders `index.html`. Running this file directly starts the development server.
- `templates/base.html` defines the shared HTML page, heading, navigation and
  stylesheet link. Its Jinja2 blocks let other templates supply a title and content.
- `templates/index.html` extends `base.html` and supplies the homepage content.
- `static/css/style.css` sets a white background, black text, basic spacing and
  a readable font. Flask serves this file from its built-in static route.
- `database/` is reserved for database files in later phases.
- `docs/` is reserved for project documentation. The empty `.gitkeep` files allow
  Git to track both otherwise empty folders; they have no application behavior.
- `requirements.txt` lists Flask, psycopg's binary distribution and python-dotenv.
  Flask handles requests and templates. psycopg will connect to PostgreSQL in a
  later phase. python-dotenv lets the Flask CLI load optional `.env` settings.
- `.env.example` is a safe example of a Flask setting with no credentials. Copy
  it to `.env` if you want local settings; this is optional for Phase 1.
- `.gitignore` excludes virtual environments, generated Python files and local
  environment files containing potential secrets.
- `README.md` explains setup, the code and manual testing.

## Setup and run

Install Python 3 first. Open a terminal in this `lostandFound` directory.

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
The Flask development server is intended for local development.

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
