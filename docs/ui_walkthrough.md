# Simple FoundDesk UI and viva walkthrough

FoundDesk uses HTML, basic CSS, Flask/Jinja2 and PostgreSQL through psycopg 3.
There is no JavaScript or frontend framework. Existing functionality is retained;
the search form now uses ordinary paragraphs and line breaks instead of flexbox.
Development rules for future changes are recorded in ../AGENTS.md.

## Every HTML template

| File in templates/ | Purpose and important elements |
| --- | --- |
| base.html | Shared page structure. h1 names the project; nav/a provide links; link loads CSS; a POST form/button logs out. main holds each page and p shows flash messages. |
| index.html | Homepage. h2 and p display real lost/found COUNT results, or an availability message. |
| register.html | form with name/email/password inputs and a submit button creates a student account. Password input hides typing. |
| login.html | Email/password form authenticates an existing account. |
| lost_item_form.html | Creates or edits a lost report. Inputs collect name/location/date, select chooses a database category, textarea collects description. |
| found_item_form.html | Equivalent create/edit form for a found report and its found date. |
| browse_items.html | GET search form with keyword, category, location and type. A table lists matching database records; item-name links open details. |
| item_detail.html | dl groups details; dt names a field and dd displays its value. Eligible students see the claim link. |
| my_reports.html | Separate lost/found tables show the logged-in user's reports. Edit links open prefilled forms; POST buttons delete eligible reports. |
| claim_form.html | select chooses an owned unresolved loss; textarea records a private ownership reason; POST button submits a claim. |
| my_claims.html | Table shows the user's claims, linked items, date, status and private reason. |
| admin.html | Pending-claim table joins claimant and item information. Separate POST buttons approve or reject each claim. |
| reports.html | Tables display totals, category counts, claim statuses, unresolved losses and returned finds. Admin access is required. |
| report_totals.html | Shared table fragment included by admin/reports pages; it is not a separate route. |

In tables, tr is a row, th labels a column and td contains a value. thead and
tbody separate column headings from data. scope="col" identifies column headers
for assistive technology. Labels explain fields; for/id connects separate labels
and controls, while a label wrapping an input also connects them.

An input's name is the key Flask receives, and value supplies its current value.
required, maxlength and date max help browser validation; Flask must still validate
submitted values because clients can bypass browser checks. disabled prevents
submitting report forms when categories/database are unavailable.

Every POST form includes a hidden csrf_token input. It travels with the form and
must match the session token. It does not replace login or ownership checks.
role="alert" identifies errors; role="status" identifies feedback messages.

Jinja's extends uses base.html, block fills a page section, include reuses the
totals fragment, for repeats rows/options, and if chooses what to show.
{{ value }} prints escaped text; url_for builds route URLs. The short expressions
for selected preserve chosen options, and edit conditions reuse create forms.

## What the CSS does

static/css/style.css keeps a white background, black text/links, Arial font and
readable line height. Margin separates the page from the window and the horizontal
rule from content. Table border-collapse combines adjacent borders; borders and
padding separate cells, text-align aligns headings with values, and vertical-align
keeps long cells aligned at the top. The logout form uses display: inline so it
fits in navigation. white-space: pre-wrap preserves description/reason line breaks.
These are small formatting rules; there is no animation or advanced layout.
The search form uses p and br like the other forms and needs no layout CSS.

## How a request works

1. A link or GET form requests a page. Search fields appear in the URL; Flask reads
   them with request.args. GET requests read data and do not change records.
2. A POST form sends named fields in its request body to its action URL. Flask
   reads request.form. The CSRF check runs before the route; protected routes also
   check the signed login session, role and ownership as appropriate.
3. Flask validates values. db.get_connection opens PostgreSQL with dictionary rows.
   cursor.execute(query, parameters) binds user values to %s placeholders separately
   from SQL syntax. The placeholders are not Python string interpolation.
4. SELECT results are read with fetchone/fetchall and passed to render_template.
   Jinja loops produce table rows; the browser receives finished HTML.
5. Writes commit when the connection's with block exits successfully. Errors roll
   back the transaction. After a successful write, redirect loads a fresh page and
   flash supplies feedback. This avoids repeating the POST on ordinary refresh.

For example, reporting a loss posts item_name/category_id/description/location/
lost_date. Flask obtains user_id from the session, validates the category/date,
executes INSERT INTO lost_items with status 'Lost', commits and redirects to
/my-reports. That page runs SELECT again and prints the saved row in its table.

## Every route and its SQL

The SQL below describes the existing statements in app.py; read that file for
complete column lists and parameters. No new database/schema changes were needed.

| URL and Flask function | Queries and displayed result |
| --- | --- |
| GET / — index | Scalar SELECT COUNT(*) subqueries on lost_items/found_items; index.html prints totals. |
| GET/POST /register — register | GET opens form. Valid POST SELECTs users by email, then INSERTs full_name, email, password_hash and fixed student role. Redirects to login after commit. |
| GET/POST /login — login | POST SELECTs user_id/password_hash/role WHERE email = %s; Python checks the hash and stores user_id/role in the signed session, then redirects home. Invalid credentials show feedback. |
| POST /logout — logout | Clears session and redirects; no SQL. |
| GET/POST /report-lost — report_lost | SELECT categories ORDER BY category_name populates select. Valid POST INSERTs lost_items with session owner and 'Lost' status; redirects to My Reports. |
| GET/POST /lost-items/<lost_id>/edit — report_lost | SELECTs an owned Lost row to prefill fields. POST UPDATEs its five report fields WHERE lost_id/user_id/status match; RETURNING confirms the update. |
| GET/POST /report-found — report_found | Loads categories and INSERTs found_items with session owner and 'Available' status; redirects to My Reports. |
| GET/POST /found-items/<found_id>/edit — report_found | Prefills an owned Available row, then UPDATEs its fields with ID/owner/status predicates and RETURNING. |
| GET /my-reports — my_reports | Two SELECTs JOIN categories, WHERE user_id = %s, ORDER BY event date/ID. EXISTS subqueries identify claims so the table can show deletion restrictions. |
| POST /lost-items/<lost_id>/delete — delete_lost_item | DELETE FROM lost_items WHERE lost_id/user_id match AND NOT EXISTS a referencing claim, RETURNING lost_id. Feedback and redirect refresh the table. |
| POST /found-items/<found_id>/delete — delete_found_item | Equivalent guarded DELETE from found_items. Foreign keys also prevent deleting referenced reports. |
| GET /browse-items — browse_items | SELECTs from requested lost/found tables JOIN categories. Optional WHERE conditions bind ILIKE keyword/location and category ID; SQL ORDER BY sorts each list and Python merges newest first. Jinja prints the results table. |
| GET /items/<item_type>/<item_id> — item_detail | SELECT from the validated Lost/Found table JOIN categories WHERE its ID = %s. The detail page shows the row; absent IDs return 404. |
| GET/POST /found-items/<found_id>/claim — submit_claim | SELECTs the found row and owned unresolved losses for the dropdown. POST locks found then lost rows with FOR UPDATE, checks eligibility and SELECTs for a duplicate pair; INSERT INTO claims creates a Pending record dated CURRENT_DATE. Redirects to My Claims. |
| GET /my-claims — my_claims | SELECT claims JOIN lost_items JOIN found_items WHERE claimant_id = %s ORDER BY claim date/ID; table shows only that user's claims. |
| GET /admin — admin_dashboard | load_report_totals runs scalar COUNT subqueries. A SELECT JOINs claims/users/lost_items/found_items WHERE status = 'Pending' ORDER BY date/ID; table displays review buttons. |
| POST /admin/claims/<claim_id>/reject — decide_claim | Reads claim IDs, UPDATEs only a Pending claim to Rejected with RETURNING. Redirects to dashboard; item statuses remain unchanged. |
| POST /admin/claims/<claim_id>/approve — decide_claim | Reads claim IDs, locks found/lost and related claims, and rechecks eligibility. Four UPDATE statements approve the chosen claim, mark found Returned, mark lost Resolved, and reject overlapping Pending claims. All commit together; redirect refreshes dashboard. |
| GET /reports — reports | Totals use subqueries/COUNT. Category totals LEFT JOIN separately grouped lost/found counts, using COALESCE for zeros. Claim totals GROUP BY status and COUNT non-null claim IDs. Joined WHERE/ORDER BY SELECTs list unresolved/returned items. Tables display all results. |

The login_required/admin_required decorators are small shared access checks;
removing them to reduce syntax would remove security. Claims' locks and transaction
boundaries also remain because multiple updates must stay consistent.

## DBMS concepts retained

database/schema.sql defines primary/foreign keys, relationships, NOT NULL, UNIQUE
and CHECK constraints. Account/category details are separated from reports.
There is an existing normalization caveat: owner-only claiming makes claimant_id
derivable from lost_id, so claims is not strictly in 2NF/3NF. See database_design.md;
this UI change does not silently redesign the existing schema.

CRUD is performed through real forms and queries above. Joins, WHERE, ORDER BY,
GROUP BY, COUNT and subqueries appear in app.py. database/queries.sql Q5 demonstrates
HAVING COUNT(...) >= 2, and Q9 demonstrates a temporary view inside a rolled-back
transaction. HAVING and that view are SQL teaching demonstrations, not additional
web features or prerequisites for running Flask. No fake records replace SQL reads.

## Testing this interface

From FoundDesk on macOS/Linux:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m flask --app app run
```

For a new checkout install requirements in a virtual environment first. Configure
your own SECRET_KEY and PostgreSQL DATABASE_URL in .env as described in README.md.
Initialize schema.sql only on a fresh database, then run sample_data.sql for
categories. Preserve existing databases. On Windows use .venv\Scripts\python.exe.

1. Open http://127.0.0.1:5000/. Check homepage and registration/login links.
2. Register two student accounts. With student A, submit a lost report; check My
   Reports, edit it, and confirm the new value after refresh.
3. Create a spare unclaimed report, delete it and confirm it disappears.
4. With student B, submit a corresponding found report. Check its edit/delete flow
   using another spare report, leaving the corresponding find available.
5. With A, search by keyword/category/location/type. Check selected filters persist,
   clear filters, and open the found item details.
6. Submit an ownership claim with A's unresolved loss and a private reason. Check
   My Claims shows Pending; check B cannot read A's private reason.
7. Register an intended admin, promote only that account using trusted local SQL
   as described in README.md, then log in again. Verify Pending Claims and Reports.
8. Approve the claim. Refresh My Claims/My Reports: Approved, Returned and Resolved
   should appear. Reports with claims must resist deletion. Use a separate eligible
   claim to test rejection, which should leave item statuses unchanged.
9. Check empty searches, missing fields, invalid dates, signed-out access and
   student requests to admin routes. Temporarily unavailable PostgreSQL must show
   an error rather than successful writes or fabricated zero totals.

Current revision check (2026-11-08): all 42 existing non-DB tests passed. These test
validation, access/CSRF, template rendering/escaping and database-unavailable paths.
The connection probe could not reach the configured PostgreSQL database here.
Successful real CRUD/claim workflows and browser layout were not reverified in
this revision. Phase 12 evidence in other documents describes an earlier run.

## Three viva questions

1. **How does HTML communicate with PostgreSQL?** The form sends a request to a
   Flask route. Flask validates it, executes parameterized SQL through psycopg,
   then renders database rows as HTML or redirects after a committed write.
2. **Why does search use GET while deletion uses POST?** GET retrieves records and
   exposes reusable filters in the URL. POST changes records and requires the
   session's CSRF token plus server-side permission checks.
3. **Why is claim approval a transaction?** The claim and both reports must change
   together. If one statement fails before commit, all changes roll back; row locks
   help competing requests avoid approving conflicting claims.
