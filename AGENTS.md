# FoundDesk development requirements

The professor requires a working database user interface. Keep this a simple
college DBMS mini project that every team member can explain in a viva.

- Inspect existing code and the current phase before changing it. Preserve working
  features; do not rewrite working code or expand the phase unnecessarily.
- Use HTML, basic CSS and Flask Jinja2 templates. Use plain forms, buttons, links
  and tables, white backgrounds and dark text. No React, Bootstrap, Tailwind,
  JavaScript frameworks, animations, advanced components or unnecessary libraries.
- Prefer simple template inheritance, conditions and loops, basic CSS properties,
  meaningful names and short comments. Avoid advanced layouts and nested markup.
- Keep Flask functions readable. Avoid unnecessary classes, decorators and
  abstractions; retain authentication, authorization, CSRF, hashing and validation.
- Use PostgreSQL through psycopg 3 with readable parameterized SQL. No ORM or
  substitute database. Forms must use real database operations, never hardcoded
  records presented as persisted data.
- Preserve homepage, registration/login, lost/found reports, browse/search,
  My Reports, ownership claims, My Claims, admin verification and database reports.
- Preserve keys, relationships, constraints, normalization work, CRUD, joins,
  WHERE/ORDER BY, GROUP BY/HAVING, aggregates, subqueries, views where appropriate
  and transactions/locking where required. Document existing normalization caveats.
- If PostgreSQL is unavailable, retain its implementation and state which checks
  could not run. Historical evidence does not establish a new successful test run.
- Explain changed pages, important HTML elements, CSS, form-to-Flask communication,
  routes, SQL and how results appear in beginner-friendly language. Keep the UI
  walkthrough current in docs/ui_walkthrough.md.
- Final handoffs should include changes, modified files, UI and request/database
  explanations, testing steps/results, three viva questions with answers and one
  suggested Git commit message.
