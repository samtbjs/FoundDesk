# FoundDesk testing checklist — Phase 11 draft

Every manual end-to-end/database/security case below is **NOT YET RUN**. Run
against local PostgreSQL during Phase 12 after installation/configuration; do not
substitute SQLite or mocks. Automated non-DB evidence is tracked separately, not
used to mark a PostgreSQL case passed. The project is not complete at Phase 11.

For Phase 12, record each actual result as PASS/FAIL with date, tester, exact
commands/inputs, relevant row IDs, expected versus observed behavior, and an
evidence path. Do not record passwords, connection strings or session cookies.
Fix failures and rerun affected tests. Keep NOT YET RUN until execution occurs.

## Automated checks (no PostgreSQL)

Verified locally on 2026-11-08 during Phase 11:

| Check | Actual result | Scope |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m compileall -q app.py db.py tests` | PASS | Python compilation only |
| `.venv\Scripts\python.exe -m unittest discover -s tests -v` | PASS — 42 tests | Access/validation/templates, password hash helper, missing-DB paths, startup guard |
| Load every template through `app.jinja_env.get_template()` | PASS — 14 templates | Jinja syntax/loadability, not browser or DB behavior |
| `git diff --check` | PASS | No whitespace errors |
| `git ls-files .env .env.example` and `git check-ignore .env` | PASS | .env.example tracked; .env untracked and ignored; contents were not displayed |

The local interpreter needed execution outside the sandbox; the checks above ran
with approved local interpreter access. No PostgreSQL server test was attempted.
Tests deliberately clear DATABASE_URL for failure paths, set test sessions directly
and render templates from input dictionaries. These are not successful database
reads, mock databases or end-to-end browser tests. Configuration tests import the
app in child processes with explicit secrets and empty DATABASE_URL.

## Installation, authentication, CRUD and security

Use a disposable local database with students A/B/C and an intended admin. Use
actual account/report IDs; do not assume generated IDs or use real personal data.

| ID | Status | Procedure and expected result |
| --- | --- | --- |
| SET-01 | NOT YET RUN | Install PostgreSQL, connect to localhost:5432, create a fresh founddesk test DB; record actual PostgreSQL/Python/dependency versions. |
| SET-02 | NOT YET RUN | Run schema.sql once; inspect all five tables, types, identity/PK/FK/UNIQUE/NOT NULL/CHECK/defaults in pgAdmin. |
| SET-03 | NOT YET RUN | Run sample_data.sql twice; the fresh DB must still have six categories and no seeded users/passwords. IDs need not be consecutive. |
| SET-04 | NOT YET RUN | Configure private .env and random key; launch Flask. Verify startup guard rejects the example secret and valid configuration connects to PostgreSQL. |
| AUTH-01 | NOT YET RUN | Register A with mixed-case/space-padded email; check normalization, student role and one persisted user row; password_hash differs from password and verifies with Werkzeug. |
| AUTH-02 | NOT YET RUN | Repeat the same normalized email, including concurrent registrations; only one user exists and the duplicate gets a friendly message. |
| AUTH-03 | NOT YET RUN | Bypass browser validation: empty/oversized name/email, malformed email, short/oversized password, mismatched confirmation must not insert. Passwords are not redisplayed. |
| AUTH-04 | NOT YET RUN | Log in with correct credentials; confirm session/own reports. Wrong/unknown credentials must not authenticate; logout clears access. Test back-button refresh after logout. |
| AUTH-05 | NOT YET RUN | Submit forged role/user_id fields at registration/login; server role/account selection must ignore them. Promote intended admin with trusted SQL and log out/in. Document that existing sessions retain cached roles after DB changes. |
| CRUD-01 | NOT YET RUN | As A create lost and found reports; query persisted fields/owner/category/date/default status; check My Reports and home counts. |
| CRUD-02 | NOT YET RUN | Edit A's eligible lost/found reports; all five fields persist and owner/status stay unchanged. |
| CRUD-03 | NOT YET RUN | Bypass browser checks: blank/whitespace required values, >150 name, >200 location, invalid/nonexistent/out-of-range category, invalid/future date must not write. |
| CRUD-04 | NOT YET RUN | As B directly GET/POST edit and POST delete A's IDs with B's valid CSRF token; A's records must stay unchanged. B's My Reports excludes A's data. |
| CRUD-05 | NOT YET RUN | Set test reports to Resolved/Returned through a legitimate approval; stale/direct edit must fail. Pending-claim reports may still be edited while Lost/Available. |
| CRUD-06 | NOT YET RUN | Delete owned reports with no claims, verify DB rows and counts. Any referencing claim, including Rejected, must block deletion through route and FK. |
| SEC-01 | NOT YET RUN | For every state-changing form, missing/wrong CSRF prevents a DB write; valid CSRF with unauthorized role/account also prevents writes. GET cannot delete/logout/decide. |
| SEC-02 | NOT YET RUN | Anonymous protected GETs redirect to login; student admin/Reports requests with valid tokens where needed give 403. Unknown routes do not disclose data. |
| SEC-03 | NOT YET RUN | Submit SQL-looking names/emails/search/reasons; inspect stored data and filtered results to confirm input remains data and tables/authorization stay intact. |
| SEC-04 | NOT YET RUN | Store HTML-like text via actual forms; browse/details/My Reports/My Claims/admin/Reports escape it and no script runs. Nonclaimants cannot read reasons, even by changing query parameters. |
| SEC-05 | NOT YET RUN | Stop server or use wrong credentials/missing schema; no successful mutation message or leaked credentials/SQL traceback. Restore valid config and verify recovery. Existing home/report routes may use friendly 200/redirect errors; newer DB pages use 503. |
| DB-01 | NOT YET RUN | In a disposable DB transaction, separately attempt invalid FK, duplicate email/category/pair, NULL required column, invalid role/status. Expect relevant constraints; roll back each failed transaction. |
| DB-02 | NOT YET RUN | Attempt delete of referenced users/categories/reports; ON DELETE RESTRICT prevents it and leaves related rows intact. |
| UI-01 | NOT YET RUN | Exercise every page/form in a browser, keyboard navigation and narrow viewport; verify real links, labels, tables, validation and no missing template/style assets. |
| DOC-01 | NOT YET RUN | Capture real screenshot placeholders S01–S10 and actual SQL outputs after tests pass. Reconcile report/README/viva with results and record acceptance; do not mark project complete before this. |

## Phase 7: Browse and details

1. **NOT YET RUN** — Register/log in and create lost and found reports with different categories,
   locations and dates. Include two reports on the same date and reports whose
   lost/found IDs overlap. Record their actual IDs for the detail URLs below.
2. **NOT YET RUN** — Visit `/browse-items`. Confirm both types appear in one table, newest event date
   first (then ID descending, then type descending for ties). All statuses appear.
3. **NOT YET RUN** — Search keyword `keys` and location `library` against names/locations containing
   uppercase letters. Confirm partial, case-insensitive matching. Keyword searches
   the item name, not description. Blank values omit their filter.
4. **NOT YET RUN** — Try every category and Lost/Found/All; combine all four filters and confirm
   AND behavior. Verify selected values remain visible and Clear filters resets them.
5. **NOT YET RUN** — Use a unique nonexistent keyword; expect the no-results message. Test a category
   with no items, and an empty database with categories seeded.
6. **NOT YET RUN** — Search quotes and SQL-looking text such as `' OR 1=1 --`. It must remain a bound
   value and not broaden results. `%` and `_` deliberately have PostgreSQL ILIKE
   wildcard meaning; test these too.
7. **NOT YET RUN** — Click each type's item link. Confirm name, description, readable category,
   location, correct lost/found date and status match the database. Check matching
   numeric IDs open the correct type. No reporter credentials are shown.
8. **NOT YET RUN** — Open `/items/Lost/<missing-id>` and `/items/Found/<missing-id>` using actual
   unused positive IDs: expect 404. Unknown types and out-of-range IDs also give 404.
9. **NOT YET RUN** — Submit category IDs that are malformed, zero, oversized or absent from the
   categories table: expect 400. Unknown types and oversized search text give 400.
10. **NOT YET RUN** — Log out: browse and detail URLs must redirect to login. Log in as another
    student: browsing should include other students' reports, without edit actions.
11. **NOT YET RUN** — Stop PostgreSQL: browse/detail should return 503 with a friendly message,
    without credentials or a misleading no-results message. Restart and retry.
12. **NOT YET RUN** — Store HTML-like names/descriptions using the report form; confirm browse and
    detail pages escape them. Check the search row and tables in a narrow window.

## Phase 8: Claims (all PostgreSQL checks unverified)

1. **NOT YET RUN** — Create students A and B, an admin, A's unresolved lost report, B's unresolved
   lost report, and an Available found report owned by B. Log in as A and open B's
   found item. Submit a reason with A's lost report. Confirm one claim row with
   A as claimant, the correct lost/found IDs, CURRENT_DATE and Pending status.
   Confirm the lost/found statuses remain Lost and Available.
2. **NOT YET RUN** — Confirm My Claims displays the correct two item links, date, Pending status and
   private reason. Log in as B: A's claim/reason must be absent even though B owns
   the found report. Adding `?claimant_id=<A-id>` must not bypass session filtering.
   Browse, item details and My Reports must not display private reasons.
3. **NOT YET RUN** — Inspect the dropdown: only A's Lost reports appear. POST B's lost_id, a missing
   lost_id, and a Resolved lost_id using A's valid CSRF token: no INSERT should occur.
4. **NOT YET RUN** — Try claiming A's own found item via direct GET/POST: expect 403. Admin submissions
   also give 403. Logged-out requests redirect to login (POST needs valid CSRF first).
5. **NOT YET RUN** — Try Returned and missing found reports: expect 409 and 404 respectively. Open
   a claim form then change either report's eligibility in another DB session.
   POST must recheck ownership/status and reject stale eligibility.
6. **NOT YET RUN** — Resubmit the same pair, including concurrent submissions: only one row may exist,
   with a friendly duplicate error (409). Existing Pending/Approved/Rejected pairs
   all block duplicates. Different eligible lost/found pairs remain allowed.
7. **NOT YET RUN** — Verify blank/whitespace reasons, >2000-character reasons, malformed/out-of-range
   lost IDs, and missing/wrong CSRF cannot insert. SQL-looking input must stay data;
   HTML-like reasons must render escaped in My Claims and the form after an error.
8. **NOT YET RUN** — In POST data supply forged claimant_id, status and claim_date. Confirm INSERT
   still uses session user ID, Pending and CURRENT_DATE. Verify no UPDATE of item
   statuses occurs. Test transaction rollback on DB error and success only after commit.
9. **NOT YET RUN** — With no unresolved lost reports, confirm the explanatory message and Report Lost
   link. With no claims, confirm My Claims empty state. During an outage, GET/POST
   and My Claims must return 503 without false success, empty state or credentials.
10. **NOT YET RUN** — Attempt deletion of either claimed report through existing routes: claims' FKs
    and application checks must prevent it. Repeat prior report/search checks.
11. **NOT YET RUN** — Concurrently update/delete the selected reports while posting a claim. Confirm
    row locks serialize eligibility checks and insertion without a stale eligible
   claim; database errors must be handled. Use the Phase 9 cases below for admin review.

Use actual IDs from the test database, then inspect in psql/pgAdmin:

```sql
SELECT c.claim_id, c.claimant_id, c.lost_id, c.found_id, c.claim_date, c.status,
       l.user_id AS lost_owner, l.status AS lost_status,
       f.user_id AS found_owner, f.status AS found_status
FROM claims AS c
JOIN lost_items AS l ON l.lost_id = c.lost_id
JOIN found_items AS f ON f.found_id = c.found_id
ORDER BY c.claim_id DESC;
```

## Phase 9: Admin decisions (all DB/transaction/concurrency checks unverified)

Setup: register students A/B/C and an administrator account, promote only the
intended admin through trusted local SQL, then log out/in to refresh its session
role. Use actual IDs, valid CSRF tokens and a disposable local test database.

1. **NOT YET RUN** — Confirm logged-out admin requests redirect to login; student admin GETs and
   POSTs with valid CSRF give 403. GET on either decision URL gives 405. Missing or
   wrong CSRF cannot change data. The Admin link appears only for admin sessions.
2. **NOT YET RUN** — Submit claims from different students. `/admin` must display only Pending claims,
   oldest date/ID first, with claimant name, item IDs/names/links, escaped private
   reason, date, and two POST forms. Students must still see only their own claims
   in My Claims; public report/detail pages must not disclose reasons.
3. **NOT YET RUN** — Prepare pending pairs (L1,F1), (L2,F1), (L1,F2), plus unrelated (L3,F3).
   Approve (L1,F1). Check that this claim is Approved, F1 Returned, L1 Resolved,
   both competing claims Rejected, and the unrelated pair is still Pending.
   Previously Rejected claims stay Rejected. Confirm all changes commit together.
4. **NOT YET RUN** — Reject the unrelated claim. Only its status must change to Rejected; both item
   statuses must remain unchanged. Repeated approve/reject requests on any decided
   claim give 409. Unknown action, missing claim, zero/oversized ID give 404.
5. **NOT YET RUN** — With a Pending claim, manually set its found status Returned or lost status
   Resolved using pgAdmin. Approval gives 409 and must change nothing. Also test
   an inconsistent preexisting Approved claim for either item while statuses are
   manually reset: the explicit approved-conflict check must prevent a new approval.
6. **NOT YET RUN** — Use two admin sessions and two pending claims sharing F1. Submit approvals
   concurrently: at most one succeeds, its competitor becomes Rejected, and the
   other request gives 409 after waiting. Repeat with two claims sharing L1 and
   different found items. The unused found item must remain Available.
7. **NOT YET RUN** — Repeat with crossing pairs (L1,F1), (L2,F2), (L1,F2), (L2,F1), approving the first
   two concurrently. They can both succeed; the crossing claims become Rejected.
   Ordered claim locks should avoid locking the overlaps in opposite orders.
8. **NOT YET RUN** — Race approve and reject of the same claim. Exactly one decision succeeds; the
   other gives 409. If rejection wins, item statuses remain unchanged. If approval
   wins, item statuses and conflicting claims must match the committed approval.
9. **NOT YET RUN** — Race claim submission against approval sharing a found or lost item. The common
   found-then-lost lock order must ensure submission either precedes the decision
   and is included among conflicts, or sees ineligible status and does not insert.
10. **NOT YET RUN** — Test rollback on a failure after the first approval UPDATE in a disposable DB.
    One reproducible approach in psql/pgAdmin is to temporarily add this constraint:
    `ALTER TABLE found_items ADD CONSTRAINT phase9_test_failure CHECK (status <> 'Returned') NOT VALID;`
    Approve an otherwise eligible Pending claim: expect 503 and verify the claim is
    still Pending, both original item statuses remain, and no competitors changed.
    Remove the test constraint afterward:
    `ALTER TABLE found_items DROP CONSTRAINT phase9_test_failure;`
    NOT VALID permits existing Returned rows but still checks new updates. Never
    apply this deliberate failure constraint to a real-use database.
11. **NOT YET RUN** — Stop PostgreSQL: dashboard/decisions return 503 without private connection data,
    false success or a false empty state. Restart and refresh before retrying a
    decision, especially if a connection was lost during commit.
12. **NOT YET RUN** — Confirm approved reports are no longer editable/claimable via prior routes and
    claim-linked deletion remains blocked. My Claims must reflect all decisions.

Verification queries (run as the local test DB owner):

```sql
SELECT c.claim_id, c.lost_id, c.found_id, c.status AS claim_status,
       l.status AS lost_status, f.status AS found_status
FROM claims AS c
JOIN lost_items AS l ON l.lost_id = c.lost_id
JOIN found_items AS f ON f.found_id = c.found_id
ORDER BY c.claim_id;

-- Both duplicate-approval checks should return no rows.
SELECT found_id, COUNT(*) FROM claims WHERE status = 'Approved'
GROUP BY found_id HAVING COUNT(*) > 1;
SELECT lost_id, COUNT(*) FROM claims WHERE status = 'Approved'
GROUP BY lost_id HAVING COUNT(*) > 1;
```

## Phase 10: SQL reports (all database checks unverified)

1. **NOT YET RUN** — With an empty initialized database, log in as admin. Dashboard/Reports totals
   must be zero. Seeded categories must appear with zero lost/found counts and
   all three claim statuses must appear with zero counts. Item lists are empty.
2. **NOT YET RUN** — In a disposable test database, create two lost and three found reports in one
   category. The report must show 2/3, never 6/6. Keep another category unused to
   verify LEFT JOIN zeros. Compare category column sums to overall item totals.
3. **NOT YET RUN** — Add Pending/Approved/Rejected claims through the application workflows. Compare
   the claim status counts and Pending total with direct COUNT queries. Approve
   a claim and verify Returned increases while overall lost/found totals stay fixed.
4. **NOT YET RUN** — Unresolved list must include only Lost; returned list only Returned. Compare
   names/categories/locations/event dates and links to the real rows. Newest dates
   come first with descending IDs for date ties. Do not infer a return date from
   found_date. No private reasons/account data should appear on Reports.
5. **NOT YET RUN** — With no concurrent writes, compare queries.sql Q2–Q4, Q6–Q7 against the page.
   Test Q5 below/at/above its HAVING threshold and Q8 with no, Pending and decided
   claims. SQL execution is not covered by the Python template tests.
6. **NOT YET RUN** — Run complete Q9 and Q10 blocks twice in pgAdmin/psql. Verify rollback removes
   temporary objects and application data/identity sequences stay unchanged. Never
   replace the temporary demo targets with application tables.
7. **NOT YET RUN** — Logged-out Reports requests must redirect to login and student requests give
   403. Stop PostgreSQL: dashboard/Reports must return 503 without partial/zero
   summaries or credentials. Restore the server and verify recovery.
8. **NOT YET RUN** — Verify escaped item/category/location text and plain tables in a narrow window.
   Repeat prior admin/claim/report checks after these changes.

See sql_reports.md for each query's meaning and precise pgAdmin execution steps.

## Commands after PostgreSQL installation (PowerShell)

```powershell
# From the project root; use the database password at PostgreSQL's prompt.
psql -h localhost -p 5432 -U postgres -c "CREATE DATABASE founddesk;"
psql -h localhost -p 5432 -U postgres -d founddesk -f database/schema.sql
psql -h localhost -p 5432 -U postgres -d founddesk -f database/sample_data.sql
# Configure DATABASE_URL and SECRET_KEY in .env (see .env.example).
.\.venv\Scripts\python.exe -m flask --app app run
```

Skip database creation/schema execution if already initialized; the schema is not
an incremental migration. Use a fresh test database for destructive manual checks.
