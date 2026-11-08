# Phase 11 static review

Historical snapshot: the remaining-verification notes below describe the end of
Phase 11. Phase 12 has since exercised the core PostgreSQL/browser workflows;
see [current local results](local_integration_results.md) and testing_checklist.md.

Status: draft review completed; PostgreSQL integration and project acceptance are
pending Phase 12. This review does not certify successful database operations.

## Scope and method

Read app.py, db.py, the SQL schema/seed/demo scripts, HTML templates, stylesheet,
configuration example/ignore rules, tests and existing design/report/checklist docs.
Followed the route decorators, submitted fields, bound SQL values, status checks
and transaction boundaries. Reviewed code and documentation locally without
connecting to PostgreSQL or substituting another database. Non-DB automated checks
are recorded separately in testing_checklist.md: Python compilation, all 42 tests
and loading all 14 Jinja templates passed on 2026-11-08.

## Findings and action

| Area | Static finding | Action or remaining verification |
| --- | --- | --- |
| Signing key | A missing key was rejected, but the known example key and whitespace were accepted. Anyone knowing a signing key can forge session contents. | Fixed startup validation in app.py. Reject empty/whitespace and the exact shipped placeholder. Added process-level startup regression checks; no actual key is displayed or changed. Users must still generate a strong key. |
| Setup documentation | README began with obsolete Phase 1 navigation and startup instructions preceding current configuration. | Replaced with a current setup, usage, validation and documentation index. Historical implementation details remain in Git history. |
| Test evidence | Checklist called checks unverified as a group, but did not label each manual case. Earlier-phase sections bundled several checks. | Marked every manual case NOT YET RUN; expanded installation/authentication/CRUD/security cases and retained detailed claim/report/concurrency procedures. |
| SQL parameters | User values are passed separately to execute(). Browse concatenates only fixed SQL conditions; its input remains bound. Type-specific details use fixed query branches. | No SQL construction change needed. Real injection/SQL syntax/parameter adaptation checks remain unexecuted. |
| Access | Public home/register/login; login required for item/report/claim reads and reporting; claim submission checks student role; admin/dashboard/reports check admin role. Owner predicates protect item edit/delete. | Confirm actual account/session/ownership behavior with PostgreSQL in Phase 12. |
| CSRF and methods | Global before_request checks state-changing methods using a session token and constant-time byte comparison. Forms include tokens; logout/delete/decisions use POST. | Unit checks cover missing/wrong/unicode tokens. Real authenticated write rejection remains NOT YET RUN. CSRF runs before route authorization, so an invalid token redirects home before a role/login response. |
| Passwords and sessions | Werkzeug hashes passwords and verifies hashes; login clears the previous session; logout clears it again. Cookies are HttpOnly and SameSite=Lax. | PostgreSQL hash persistence/login remains unverified. Default Flask sessions are signed, not encrypted; passwords/reasons are not stored in them. |
| Role changes | Role is loaded at login and stored in the signed session. It is not re-read from users on every request. | Documented: trusted local setup must log out/in after role changes. Existing sessions do not immediately reflect demotion/deletion. No revocation feature was added to this mini project. |
| Privacy/HTML | Only My Claims selects its claimant's reasons, while admin review can read all Pending reasons. Shared details/report summaries omit reasons and account credentials. Jinja autoescaping is kept; no safe filter is applied to user text. | Verify real multi-account isolation and stored HTML escaping in Phase 12. |
| Validation/schema | Names/categories/locations/dates match DDL. Categories must exist; dates cannot be future; claim reason is trimmed and capped at 2000 in application code. DDL has matching roles/statuses/FKs and unique pairs. | Blank fields, ownership and cross-table status rules are application checks, not all DB CHECK constraints. Direct SQL can bypass them. |
| Claims | Submission rechecks owned Lost/other-owned Available reports and locks found then lost rows. Duplicate SELECT plus UNIQUE protect the pair. INSERT uses session claimant, CURRENT_DATE, Pending. | Successful insert, FK/unique failures, and submission races remain unverified. |
| Decisions | Approval locks found then lost, then overlapping claim rows by ID; checks Pending/eligible ownership/status and existing approvals; applies four writes in one connection transaction. Reject conditionally updates Pending only. | Locking logic reviewed statically; real conflict races, deadlocks and rollback tests remain NOT YET RUN. No claim of proven concurrency behavior. |
| Connection/transactions | .env loads relative to db.py; connection has a five-second timeout and dict rows. Connection/cursor contexts close resources; exceptions roll back. Success messages occur after transaction exit. | Real credentials/server/schema/commit outcomes remain unverified. Connection loss during commit can leave the outcome uncertain: refresh before retrying. |
| Reporting | Separate item aggregates prevent category join multiplication; LEFT JOIN/COALESCE include zero categories; COUNT(claim_id) includes zero claim statuses correctly. Returned means found status Returned, not approval count. | DB totals, joins and zero cases remain unverified. Multiple SELECTs can observe different committed moments while data changes. |
| SQL demos | Q1–Q8 read application data. Q9/Q10 use temporary objects and rollback. Demo category identity is separate from application identity sequences. | Do not install demos as migrations. Run complete demo transactions in Phase 12 and verify no application changes. |
| Normalization | Entity tables avoid repeated user/category facts. Owner-only claims make claimant_id dependent on lost_id. | Kept the required schema and documented the claims 2NF/3NF limitation honestly. No schema redesign in Phase 11. |

## Deliberate scope limits

This is a local college project using the Flask development server. It does not
implement password reset, account revocation, rate limiting, audit history, file
uploads, automatic matching, pagination or a return-date field. There is no HTTPS
deployment configuration; Secure cookies would require an HTTPS setup. These are
limits of the current design, not claims that its local workflow has failed.

Home/report-form/My Reports outages use existing friendly messages and may return
200, while browse/detail/claim/admin/reports outages return 503. Invalid CSRF uses
a redirect rather than a 403. These response choices are documented, not silently
changed during the review. No broad refactor or extra feature was introduced.

## Files changed and DB operations

Code: app.py startup guard and tests/test_config.py. Documentation: README.md,
project_report.md, viva_guide.md, testing_checklist.md and this review. No schema,
seed or SQL-demo changes are needed. Phase 11 performs no database operations.
The application SQL and demo explanations are in database/queries.sql and
docs/sql_reports.md; the complete schema is in database/schema.sql.

## Phase 12 exit criteria

Install/configure local PostgreSQL; run every NOT YET RUN integration case; record
actual outcomes and any fixes; repeat affected tests; capture real screenshots;
replace draft evidence placeholders; and reconcile the report with verified
behavior. Only then assess project completion. See testing_checklist.md.
