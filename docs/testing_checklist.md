# FoundDesk testing checklist — Phase 12 actual evidence

Test date: 2026-11-08. Local Windows PostgreSQL 18.6, port 5432. Existing
founddesk data was preserved. Integration fixtures and screenshots use the separate
real database founddesk_phase12_41a2c6ee18. No SQLite or mock database was used.

PASS below means the stated covered case actually executed. It does not mark
additional unexecuted variants as passed. Tests use Flask's HTTP test client with
real psycopg connections/commits; the separate browser flow uses actual loopback
HTTP. No fabricated SQL output or screenshots are included.

## Execution ledger

| Check | Result | Evidence |
| --- | --- | --- |
| Windows service and port | PASS: postgresql-x64-18 Running; pg_isready accepting connections | local_integration_results.md |
| Existing private .env connection | PASS: local founddesk connected; no secret displayed/overwritten | evidence/phase12/environment.json |
| Isolated DB schema/seed | PASS: actual schema.sql, sample_data.sql and seed rerun | environment.json, test_constraints.json, initial_counts.json |
| Python compilation | PASS: app.py, db.py, tests, scripts | compileall exit 0 |
| Existing non-DB suite | PASS: 42 tests, rerun after integration | unittest discovery exit 0 |
| Real PostgreSQL suite | PASS: all 18 cases, 92.406 seconds in this run | evidence/phase12/integration_results.json |
| Package consistency | PASS: pip check, no broken requirements | local interpreter output |
| Requirements installation | PASS: pip install --no-index -r requirements.txt, all already satisfied | local interpreter output |
| SQL teaching script | PASS: actual psycopg and psql runs, rollback demos | query_results.json, psql_queries_output.txt |
| Browser flow | PASS: two registrations, login/logout, reports/search/claim, approve/reject, Reports/readback | 17 actual JPG captures in evidence/phase12/screenshots/ |
| Final persisted state/invariants | PASS: demo claim 21 Approved, loss 24 Resolved, find 23 Returned; no repeated Approved item IDs | evidence/phase12/final_state.json |
| Preserved DB schema comparison | PASS: original founddesk columns/constraints match tested schema | columns.json, final_state.json |

JSON/text filenames above are under docs/evidence/phase12 unless otherwise stated.
The first two failed harness attempts are retained as integration_results_attempt1.json
and integration_results_attempt2.json, with their failures explained in the local
results document. They are not relabelled PASS.

## Actual real-DB test cases

Each method below is in tests/postgres_integration.py. Run it directly; default
unittest discovery intentionally executes only the non-DB suite.

| Case | Status | What was actually checked |
| --- | --- | --- |
| 01 schema_seed_and_constraints | PASS | Five tables; PK/FK/UNIQUE/CHECK counts, repeated seed, unique category, NOT NULL, invalid role and category FK failures. |
| 02 authentication_persistence_and_duplicates | PASS | Persisted hash verification, student role despite forged role, wrong known password, normalized duplicate email rejection, real login/logout. |
| 03 crud_owner_validation_and_status | PASS | Both report types created/edited/deleted; other-user direct edits/deletes denied; owner/status preserved; empty name, nonexistent category, invalid/future date rejected without modifying the row. |
| 04 search_and_detail | PASS | Combined case-insensitive filters, both types individually/All, date order, no results, SQL-looking keyword, unknown category/missing item, escaped stored description. |
| 05 claim_privacy_duplicates_and_deletion | PASS | Pending insert, server claimant/date/status, duplicate rejection, claimant/admin visibility, other-user query-parameter bypass denied, shared pages omit reason, route/FK deletion restrictions. |
| 06 claim_eligibility | PASS | Own-found/admin GET denied, wrong-owner/missing/resolved loss rejected, Returned found rejected. |
| 07 admin_approval_and_rejection | PASS | Approval changes all required statuses, rejects same-found/same-lost conflicts, unrelated rejection leaves items unchanged, repeated approve/reject conflict, decided items no longer editable. |
| 08 csrf_access_and_no_writes | PASS | Missing/wrong token on claim/delete/both decisions cannot write; anonymous/student admin access denied; decisions reject GET. Other form/method permutations are separately covered by unit tests or remain below. |
| 09 atomic_rollback | PASS | Temporary CHECK failure after claim UPDATE rolls back all writes; remove constraint and retry succeeds. |
| 10 concurrent_shared_found_approvals | PASS | Two admin clients/real connections: one 302, one 409; Approved/Rejected claims. |
| 11 concurrent_shared_lost_approvals | PASS | One decision wins; only selected found item Returned, other stays Available. |
| 12 concurrent_crossing_pairs | PASS | Independent chosen pairs both approve while crossing competing claims become Rejected. |
| 13 concurrent_approve_reject_and_duplicate_submission | PASS | Duplicate submissions yield one insert; approve/reject race has one winner with corresponding item status. |
| 14 totals_category_zero_and_status_counts | PASS | Direct COUNT totals match page; category with 2 lost/3 found shows 2/3; unused Other remains 0/0. |
| 15 queries_sql_real_results_and_no_mutations | PASS | All read/demo result sets; before/after counts and application identity values unchanged; temporary view/table absent after rollback. |
| 16 submission_racing_approval | PASS | Races sharing found or lost item leave either no new claim or a rejected competitor; selected approval succeeds. |
| 17 real_connection_failure_and_recovery | PASS | Real closed loopback port failures give 503/unavailable responses; restoration recovers Reports. No service stop was performed. |
| 18 stale_admin_eligibility | PASS | Returned found or Resolved loss causes 409 without changing Pending claim; rejection still succeeds. |

## Browser evidence

The screenshots show actual browser state, not unit-test fixtures rendered outside
a running app. Browser account demo.owner created lost 24; demo.finder created found
23; owner submitted claim 21; admin approved 21 and rejected separate test claim 6.
My Claims read back Approved, detail pages showed Resolved/Returned, and Reports
showed actual totals. See project_report.md for links/embedded screenshots.
No browser console warnings/errors were captured in the final inspected view.
A label-based automation locator and one item-link click needed retargeting/direct
navigation to the observed href; no reproducible application defect was established.

S10 uses real psql output and constraint JSON instead of claiming a pgAdmin screenshot.
Screenshots capture successive states; their totals naturally differ as data changed.

## Remaining unexecuted variants

These remain NOT YET RUN in their full form. A related passing unit/integration
case above is not a substitute for the additional variant named here.

| ID | Status | Remaining procedure |
| --- | --- | --- |
| EXT-01 | NOT YET RUN | Full keyboard-only, narrow/mobile viewport and accessibility sweep of every form/table, including long multiline data and all validation messages. |
| EXT-02 | NOT YET RUN | Concurrent registration of the same normalized email, unknown-email DB login, exhaustive email/name/password boundary permutations, and browser back-button/cache behavior after logout. |
| EXT-03 | NOT YET RUN | Every form with forged owner/status/login fields and every boundary (text lengths, integer IDs, malformed categories, blank/2001-character reason) against the real DB; units cover many individual validators. |
| EXT-04 | NOT YET RUN | SQL-looking input and stored HTML in every name/email/location/category/reason field on every page. The executed tests cover search, stored descriptions and private reasons, not all permutations. |
| EXT-05 | NOT YET RUN | Stale ownership/account deletion/demotion with an existing session. Role caching until a new login is a documented design limitation, not immediate revocation. |
| EXT-06 | NOT YET RUN | Forced service stop/start, wrong-password and missing-schema variants. Real connection refusal/recovery was tested using closed port 1 without disrupting the user's service. |
| EXT-07 | NOT YET RUN | Network/process loss specifically during commit, prolonged stress/repeated randomized scheduling and all possible deadlock/interleaving cases. Bounded concurrency passed; no universal proof claimed. |
| EXT-08 | NOT YET RUN | Raw SQL rejection of every allowed/invalid status and deletion of every referenced parent type, including Rejected-claim deletion paths and manually inconsistent existing Approved records. Some constraints/FK deletion paths passed as listed. |
| EXT-09 | NOT YET RUN | Empty report UI after admin creation and no item/claim data, all claim-status zero combinations, every category selection/HAVING threshold boundary and repeated same-date ordering ties. Initial zero DB counts and unused-category zero counts were verified. |
| EXT-10 | NOT YET RUN | Query execution in the pgAdmin editor UI. Installed psql access/execution and actual query output have been verified instead. |
| EXT-11 | NOT YET RUN | User-specific title-page details and final submission/acceptance. No identity/course information is invented. |

## Reproduction and evidence policy

From the project root, use the commands in local_integration_results.md. Setup
creates a fresh test DB and replaces environment.json; archive the evidence folder
before reproducing if retaining these captured results. The suite refuses the
ordinary founddesk name and any populated test users table. Helpers never print
DATABASE_URL/SECRET_KEY. Test databases are retained for inspection, not dropped.

For any additional case, record date, actual input/IDs, observed response/rows,
PASS/FAIL and evidence path. Keep NOT YET RUN until execution; do not use templates
or screenshots of a different state as claimed output. Avoid credentials/session
cookies in all evidence. No blanket claim that every extended variant passed is made.
