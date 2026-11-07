# Deferred PostgreSQL integration tests

All checks below are **unverified**. Run against local PostgreSQL during Phase 12
after installation/configuration; do not substitute SQLite or mocks.

## Existing phases

- Apply `database/schema.sql` once to a new database and run `database/sample_data.sql`.
- Verify registration, duplicate emails, hashed passwords, login/logout and homepage counts.
- Verify lost/found creation, validation, persistence, ownership checks on edit/delete,
  editable statuses, CSRF rejection and deletion blocked by referencing claims.
- Follow the detailed earlier-phase manual checks in README.md. Test claim-dependent
  behavior once that workflow exists; do not implement it as part of Phase 7.

## Phase 7: Browse and details

1. Register/log in and create lost and found reports with different categories,
   locations and dates. Include two reports on the same date and reports whose
   lost/found IDs overlap. Record their actual IDs for the detail URLs below.
2. Visit `/browse-items`. Confirm both types appear in one table, newest event date
   first (then ID descending, then type descending for ties). All statuses appear.
3. Search keyword `keys` and location `library` against names/locations containing
   uppercase letters. Confirm partial, case-insensitive matching. Keyword searches
   the item name, not description. Blank values omit their filter.
4. Try every category and Lost/Found/All; combine all four filters and confirm
   AND behavior. Verify selected values remain visible and Clear filters resets them.
5. Use a unique nonexistent keyword; expect the no-results message. Test a category
   with no items, and an empty database with categories seeded.
6. Search quotes and SQL-looking text such as `' OR 1=1 --`. It must remain a bound
   value and not broaden results. `%` and `_` deliberately have PostgreSQL ILIKE
   wildcard meaning; test these too.
7. Click each type's item link. Confirm name, description, readable category,
   location, correct lost/found date and status match the database. Check matching
   numeric IDs open the correct type. No reporter credentials are shown.
8. Open `/items/Lost/<missing-id>` and `/items/Found/<missing-id>` using actual
   unused positive IDs: expect 404. Unknown types and out-of-range IDs also give 404.
9. Submit category IDs that are malformed, zero, oversized or absent from the
   categories table: expect 400. Unknown types and oversized search text give 400.
10. Log out: browse and detail URLs must redirect to login. Log in as another
    student: browsing should include other students' reports, without edit actions.
11. Stop PostgreSQL: browse/detail should return 503 with a friendly message,
    without credentials or a misleading no-results message. Restart and retry.
12. Store HTML-like names/descriptions using the report form; confirm browse and
    detail pages escape them. Check the search row and tables in a narrow window.

## Phase 8: Claims (all PostgreSQL checks unverified)

1. Create students A and B, an admin, A's unresolved lost report, B's unresolved
   lost report, and an Available found report owned by B. Log in as A and open B's
   found item. Submit a reason with A's lost report. Confirm one claim row with
   A as claimant, the correct lost/found IDs, CURRENT_DATE and Pending status.
   Confirm the lost/found statuses remain Lost and Available.
2. Confirm My Claims displays the correct two item links, date, Pending status and
   private reason. Log in as B: A's claim/reason must be absent even though B owns
   the found report. Adding `?claimant_id=<A-id>` must not bypass session filtering.
   Browse, item details and My Reports must not display private reasons.
3. Inspect the dropdown: only A's Lost reports appear. POST B's lost_id, a missing
   lost_id, and a Resolved lost_id using A's valid CSRF token: no INSERT should occur.
4. Try claiming A's own found item via direct GET/POST: expect 403. Admin submissions
   also give 403. Logged-out requests redirect to login (POST needs valid CSRF first).
5. Try Returned and missing found reports: expect 409 and 404 respectively. Open
   a claim form then change either report's eligibility in another DB session.
   POST must recheck ownership/status and reject stale eligibility.
6. Resubmit the same pair, including concurrent submissions: only one row may exist,
   with a friendly duplicate error (409). Existing Pending/Approved/Rejected pairs
   all block duplicates. Different eligible lost/found pairs remain allowed.
7. Verify blank/whitespace reasons, >2000-character reasons, malformed/out-of-range
   lost IDs, and missing/wrong CSRF cannot insert. SQL-looking input must stay data;
   HTML-like reasons must render escaped in My Claims and the form after an error.
8. In POST data supply forged claimant_id, status and claim_date. Confirm INSERT
   still uses session user ID, Pending and CURRENT_DATE. Verify no UPDATE of item
   statuses occurs. Test transaction rollback on DB error and success only after commit.
9. With no unresolved lost reports, confirm the explanatory message and Report Lost
   link. With no claims, confirm My Claims empty state. During an outage, GET/POST
   and My Claims must return 503 without false success, empty state or credentials.
10. Attempt deletion of either claimed report through existing routes: claims' FKs
    and application checks must prevent it. Repeat prior report/search checks.
11. Concurrently update/delete the selected reports while posting a claim. Confirm
    row locks serialize eligibility checks and insertion without a stale eligible
    claim; database errors must be handled. Admin claim review remains a later phase.

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
