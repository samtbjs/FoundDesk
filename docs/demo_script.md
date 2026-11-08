# FoundDesk compact demo and 10 viva answers

## Five-minute local demonstration

The tested environment is Windows/PostgreSQL 18.6. Start the normal app with
`.venv\Scripts\python.exe -m flask --app app run` after configuring .env. To inspect
the retained isolated Phase 12 data instead, use
`.venv\Scripts\python.exe scripts/phase12_server.py` and open port 5012.

The isolated DB contains `demo.owner@phase12.example.test`,
`demo.finder@phase12.example.test` and `admin@phase12.example.test`, all using the
test-only password `Phase12-test-only-Password!`. These are disposable test accounts,
not the user's database credentials or default accounts installed by schema.sql.
The demonstrated keyring claim is already Approved; create a new eligible pair
to demonstrate a fresh decision. Do not assume IDs from this run on a new database.

1. **Home/accounts (30 seconds):** show actual counts. Register/log in with two
   test students; explain password hashing and student role assignment.
2. **Reporting (60 seconds):** owner submits a lost report; finder submits an
   Available found report. Show each student's own My Reports rows.
3. **Search (30 seconds):** owner filters by name/category/location/All and opens
   the found report. Explain GET values and parameterized ILIKE/JOIN.
4. **Claim (45 seconds):** choose the owner's Lost report and enter a reason.
   Show Pending in My Claims. Explain the three foreign keys and private reason.
5. **Decision (60 seconds):** log in as admin; verify the claim and approve it.
   Show Approved, found Returned and lost Resolved. Reject a separate Pending
   claim to show that rejection does not change item statuses.
6. **Reports/SQL (45 seconds):** show totals/category/status tables. In psql/pgAdmin
   execute an actual query from queries.sql and explain COUNT/GROUP BY/LEFT JOIN.
   Mention the captured rollback/race tests and documented remaining variants.

Use the actual [results](local_integration_results.md) and report screenshots as
evidence. Never display .env, session cookies or database passwords in the demo.

## Ten typical viva questions

1. **What problem does FoundDesk solve?** It records college lost/found reports,
   connects ownership claims and tracks admin return decisions in relational tables.
2. **How does Jinja differ from JavaScript?** Jinja renders HTML on the Flask server;
   the browser receives ordinary forms/tables. No JavaScript framework is used here.
3. **Why GET and POST?** GET reads/searches using request.args; POST submits changes
   using request.form. State-changing forms require CSRF and successful writes redirect.
4. **How are passwords and sessions protected?** Werkzeug stores salted password
   hashes; Flask signs session cookies with a private random key. Signing is not encryption.
5. **What are the claim's foreign keys?** lost_id references lost_items, found_id
   references found_items, and claimant_id references users. The pair is UNIQUE.
6. **Is every table strictly in 3NF?** The four entity tables separate account/category
   facts. Claims retains redundant claimant_id under the owner-only rule, so strict
   2NF/3NF is not satisfied there; this is an acknowledged schema limitation.
7. **How is SQL injection prevented?** User values are bound separately via psycopg
   placeholders. Browse joins only fixed SQL fragments, never user SQL text.
8. **Why LEFT JOIN and pre-aggregation in Reports?** LEFT JOIN keeps unused categories;
   counting each item table first avoids multiplying rows and inflating counts.
9. **Why one approval transaction with locks?** The claim and item statuses must change
   together. FOR UPDATE makes competitors wait and recheck eligibility; other Pending
   claims sharing either item are rejected. This passed bounded real-DB race tests.
10. **What was actually tested?** 42 non-DB checks and 18 PostgreSQL integration cases
    passed; a real browser verified registration through approval/rejection and Reports.
    SQL demos ran in psql. Remaining viewport, service-stop, long-load and other detailed
    variants are listed explicitly rather than claimed as passed.
