# FoundDesk viva guide — Phase 11 draft

Explain the actual code, not an imagined feature. PostgreSQL integration evidence
is pending Phase 12; distinguish a static explanation from a test you have run.

## Frontend: HTML, CSS and Jinja

1. **How is the UI built?** Flask renders HTML/Jinja templates; basic CSS provides
   borders, spacing, black text and a white background. No frontend framework is used.
2. **What is template inheritance?** Pages extend base.html and fill its title/content
   blocks. The header, navigation, stylesheet and flash messages are shared.
3. **What are Jinja loops/conditions used for?** Loops make table rows and dropdowns;
   conditions choose login links, eligible actions, errors and empty states.
4. **How is user text displayed safely?** Jinja autoescapes HTML templates. No safe
   filter is applied to descriptions/reasons. Escaping is separate from SQL binding.
5. **Does browser validation replace Flask checks?** No. required/maxlength/date
   controls help users, but crafted requests can bypass them; Flask validates again.

## Flask routes and GET/POST

6. **What is a route?** A URL/method mapping to a Python function, such as GET
   /browse-items calling browse_items(). render_template produces the HTML response.
7. **Why GET for search?** It reads data and keeps filters in the URL. Flask reads
   them using request.args. Searches can be bookmarked.
8. **Why POST for changes?** Registration/report/claim forms send data using
   request.form. Delete/logout/admin decisions are POST-only and require CSRF.
9. **Why redirect after a successful POST?** Post/Redirect/Get takes the user to a
   GET page and reduces accidental form resubmission on refresh. UNIQUE still protects
   duplicate claim pairs even if a POST is repeated.
10. **What responses are used?** Login guards redirect to /login. Unauthorized roles
    give 403; bad search/claim selection can give 400; missing items/claims 404;
    decided/ineligible decisions 409. Several DB-dependent pages return 503 on errors.
    Older home/report routes show friendly errors with 200/redirect. Invalid CSRF
    redirects home before route guards run.

## Sessions, passwords and security

11. **What is stored in the session?** user_id and role after login, a random CSRF
    token, and flash messages. A successful login clears the old session; logout clears it.
12. **Are Flask session cookies encrypted?** Default sessions are signed, not
    encrypted. A private SECRET_KEY protects integrity; do not store confidential
    claim reasons or password data in the cookie.
13. **Why reject the example secret?** A publicly known signing key lets someone
    forge signed session contents, including an admin role. Generate your own key.
14. **How are passwords protected?** generate_password_hash stores a salted hash;
    check_password_hash verifies a login. Hashing is not reversible encryption.
15. **How are roles assigned?** Registration always inserts student. Trusted local
    SQL promotes an intended admin; login reads role from users. Users cannot choose
    an admin role in a form. Existing sessions cache roles until a new login.
16. **How does CSRF work?** Forms send a hidden random token also stored in the
    session. before_request compares token bytes with secrets.compare_digest on
    state-changing methods. Missing/wrong tokens stop the request before writes.
17. **How is ownership enforced?** SQL edit/delete predicates include the session
    user_id. Claim submission selects an owned Lost report and rejects self-found items.
18. **Who can read reasons?** My Claims restricts to the session claimant; admin
    Pending Claims review can read reasons. Shared item/report pages omit them.
19. **Does hiding a button secure a route?** No. Server decorators, SQL predicates
    and POST validation enforce access when someone requests a URL directly.

## psycopg and connectivity

20. **What is psycopg?** The PostgreSQL adapter used to open connections, execute SQL
    and fetch rows. This project uses explicit SQL instead of an ORM.
21. **Where are credentials?** DATABASE_URL and SECRET_KEY are local .env settings.
    db.py loads that file relative to itself. Git ignores .env; .env.example has placeholders.
22. **Why dict_row?** It exposes rows by names such as row['item_name'], making
    route/template code readable. get_connection also sets a five-second connect timeout.
23. **How do bound parameters work?** cursor.execute(sql, values) sends SQL syntax
    and values separately. For example `WHERE email = %s` with `(email,)`. Do not use
    f-strings to insert user values or quote the placeholder in SQL.
24. **What about the browse query's concatenation?** It joins fixed condition/order
    strings only. All user values, including ILIKE patterns, remain in the bound list.
25. **What happens on connection failure?** Routes catch psycopg.Error and show a
    friendly message. They do not print credentials or pretend successful reads/writes.
    Importing the app needs a real secret but does not connect to PostgreSQL.

## ER model, keys and constraints

26. **What are the five entities?** users, categories, lost_items, found_items and claims.
27. **What is a PK?** A unique non-null identifier. Each table has a generated
    INTEGER identity key. Identity gaps are normal; an ID is not a row count.
28. **What is a FK?** It requires a referenced parent row to exist. A report references
    an account/category; a claim references a claimant and one report of each type.
29. **What are the relationships?** One user/category has many reports; each report
    can be in many different claims. Claims links lost/found reports many-to-many.
30. **Why UNIQUE(lost_id, found_id)?** It disallows claiming the same pair twice,
    including after rejection, while allowing different pairs involving either report.
31. **What is ON DELETE RESTRICT?** A referenced user/category/report cannot be deleted
    while child rows exist. Claims are not automatically deleted with their reports.
32. **What do CHECK and NOT NULL do?** CHECK limits roles/statuses; NOT NULL forbids
    missing values. NOT NULL does not reject blank text. Application checks add more rules.
33. **Does a FK prove claim ownership/availability?** No. Those are cross-table business
    conditions checked by routes. Direct SQL must not bypass the application workflow.

## Normalization

34. **What is 1NF here?** Atomic column values and no repeating groups/lists inside rows.
35. **What is 2NF?** 1NF with no non-key attribute depending on only part of any
    candidate key. A generated primary key alone does not prove it; claims also has
    the alternate candidate key (lost_id, found_id).
36. **What is 3NF?** 2NF plus no inappropriate transitive dependency through non-key
    attributes. User/category names are kept in their own tables and referenced by ID.
37. **Is claims strictly in 3NF?** Under owner-only claiming, lost_id determines
    claimant_id through the lost report's owner. This is redundant and violates strict
    2NF/3NF for claims. The specified schema is retained; explain the caveat honestly.
38. **What anomalies are reduced?** Changing a category name or user email in one
    row avoids inconsistent repeated copies. Categories can exist before any report.

## SQL: queries, joins, aggregates and CRUD

39. **What does ILIKE do?** Case-insensitive pattern matching. `%keyword%` searches
    within item_name; `%` and `_` supplied by a user retain SQL wildcard semantics.
40. **INNER JOIN versus LEFT JOIN?** INNER JOIN keeps matched rows; LEFT JOIN keeps
    all left rows, using NULLs where unmatched. Categories with no reports need LEFT JOIN.
41. **COUNT(*) versus COUNT(column)?** COUNT(*) counts rows; COUNT(column) ignores
    NULLs. The status report counts claim_id so unmatched LEFT JOIN statuses show zero.
42. **WHERE versus HAVING?** WHERE filters individual rows; HAVING filters groups
    after GROUP BY, such as categories with at least two unresolved reports.
43. **Why pre-aggregate both item tables?** Two lost and three found rows in one
    category would make six joined rows. Separate grouped counts avoid inflated totals.
44. **What is a subquery?** A SELECT inside another query. Scalar COUNT subqueries
    calculate dashboard totals; NOT EXISTS checks for missing related claims.
45. **Why no AVG/SUM?** The schema has no meaningful prices/quantities for those
    aggregates. COUNT is appropriate for report and claim totals.
46. **What is a view?** A saved SELECT definition, not a copied snapshot. queries.sql
    creates a temporary view in a rollback demo; Flask does not need it installed.
47. **Where is CRUD?** INSERT creates accounts/reports/claims; SELECT reads them;
    UPDATE edits reports/decides claims; DELETE removes owned unclaimed reports.
48. **Are SQL demos safe for application data?** Q1–Q8 are reads. Q9/Q10 use temporary
    objects and rollback. DML targets a copied temporary category table with its own
    identity sequence, not application categories. Run complete demo blocks.

## Claims, transactions and request flow

49. **What are the statuses?** Lost reports: Lost/Resolved; found reports:
    Available/Returned; claims: Pending/Approved/Rejected. Capitalization matches CHECKs.
50. **What does submission verify?** Student role, other-owned Available find, owned
    unresolved loss, valid reason and no duplicate pair. It inserts Pending only.
51. **What is a transaction?** Work that commits as a unit or rolls back on error.
    psycopg connection contexts handle commit/rollback and close the connection.
52. **What does approval change?** Selected claim Approved, found Returned, lost
    Resolved, other Pending claims sharing either item Rejected in one transaction.
53. **Why FOR UPDATE?** It locks rows until transaction end so competitors wait and
    recheck committed eligibility. Submission/approval lock found then lost; approval
    also locks overlapping claims by ID. PostgreSQL concurrency checks are still pending.
54. **What if two admins decide the same claim?** Conditional Pending checks and locks
    are intended to allow only one decision. The other receives a conflict. This must
    be verified using actual concurrent PostgreSQL sessions in Phase 12.
55. **What does rejection change?** Only a Pending claim's status, not item statuses.
56. **How does a search reach the database?** GET values -> request.args -> validation
    -> parameterized SELECTs -> dictionary rows -> Jinja results table.
57. **How does a claim reach the database?** POST fields/token -> CSRF -> login/student
    checks -> report locks/eligibility -> parameterized INSERT -> commit -> redirect.
58. **How does admin approval reach the database?** CSRF/admin checks -> read IDs ->
    lock rows -> recheck state -> four UPDATEs -> commit -> dashboard redirect.
59. **Does any connection error prove rollback?** Errors before commit roll back on
    context exit. A dropped connection during commit can leave the outcome uncertain;
    refresh/check persisted status before retrying.
60. **What testing is still required?** Real PostgreSQL schema/constraints, login/CRUD,
    SQL search/aggregates, privacy, atomicity/concurrency, browser flows and actual
    screenshots. Non-DB tests are useful but do not prove these integration results.

## Demonstration order for Phase 12

Start PostgreSQL and Flask, register/log in with real test accounts, submit a loss
and a find, search, claim as the loss owner, review as admin, approve, and show
updated My Claims/report totals. Show a real JOIN/GROUP BY query in pgAdmin and
explain its result. Use testing_checklist.md and capture evidence only after each
step really works; no screenshots/results are supplied by this draft guide.
