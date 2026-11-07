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
