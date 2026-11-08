# Phase 10: SQL reports and query guide

## Page behavior and code walkthrough

`/admin` and `/reports` require login and the admin session role. The dashboard
adds four totals to the existing Pending Claims table; Reports contains the same
totals, category counts, claim counts, unresolved losses and returned found reports.
Neither page adds charts, scripts, account details or private claim reasons to
report summaries. Reasons remain restricted to the claimant and admin review.

`load_report_totals(cursor)` executes four scalar COUNT subqueries and returns
one dictionary. Lost/found totals include all statuses; Pending counts only claims
with that status; Returned counts found rows with that status, not approved claims.
`reports()` then runs four SELECTs and passes their dictionaries to Jinja tables.
Category counts include unused categories with zeros; all three claim statuses
appear even when their count is zero. Lost/returned lists use event dates newest
first. There is no return-date column: returned items display found_date explicitly.

Categories are aggregated separately in each report table before LEFT JOIN.
For example, two lost and three found reports in a category must count as two and
three, not six each. COALESCE converts a missing aggregate into zero. Claim counts
use a three-row VALUES table and COUNT(c.claim_id); COUNT(*) would incorrectly
count a null-extended unmatched row as one.

All route queries are fixed SQL with no user-supplied filters. No user input is
interpolated. These pages perform SELECT only; they do not depend on the demo view.
An error suppresses all partial report tables and returns 503 with a friendly
message. Empty data produces zero totals/empty lists, not an outage message.
These are separate SELECT statements under the default isolation level, so data
changing during a request can appear at different committed moments. Refresh after
claim decisions when comparing summaries; this is not a stored historical snapshot.

## database/queries.sql explanations

| Query | Purpose and SQL concepts |
| --- | --- |
| Q1 | SELECT specific unresolved-loss columns; WHERE filters Lost; ORDER BY shows newest first. |
| Q2 | Four meaningful COUNTs with scalar subqueries; independent totals avoid joined row duplication. |
| Q3 | GROUP BY category_id counts each item table first; LEFT JOIN retains unused categories; COALESCE shows zeros. Matches Reports. |
| Q4 | LEFT JOIN against the three allowed statuses; GROUP BY and COUNT(non-null primary key) include zero counts. Matches Reports. |
| Q5 | WHERE keeps unresolved losses; GROUP BY creates category groups; HAVING keeps groups with at least two unresolved reports. A teaching query, not another report-page filter. |
| Q6 | INNER JOIN returns Returned found rows with category names, ordered by found date. Matches Reports. |
| Q7 | INNER JOIN returns unresolved lost rows with category names. Matches Reports. |
| Q8 | Correlated NOT EXISTS subquery lists Available found reports with no Pending claim; decided claims do not exclude a row. |
| Q9 | CREATE TEMP VIEW names the unresolved-loss SELECT; SELECT queries it, and ROLLBACK removes the view. A normal view stores a query definition, not a snapshot. |
| Q10 | INSERT creates a category, UPDATE renames it, DELETE removes it, each with RETURNING. This demo uses an isolated temporary table copying category constraints and its own identity sequence, then rolls back. |

No AVG/SUM is added: there are no prices or quantities needing those aggregates.
COUNT is the meaningful aggregate for reports/claims. Q5 uses a literal teaching
threshold of two; changing it in the SQL editor changes only the displayed groups.

## Execute in pgAdmin after PostgreSQL installation

1. Connect to localhost:5432 and select the initialized `founddesk` database.
   Run `schema.sql` once on a new database, then `sample_data.sql`, as described in
   database_design.md. Do not rerun schema.sql over existing tables.
2. Open Tools > Query Tool for that database. Open `database/queries.sql`.
3. Select one complete Q1–Q8 statement including its semicolon and execute it.
   Inspect Data Output for rows/column headings and Messages for errors. No particular
   counts are promised: results depend on reports submitted in your local database.
4. For Q9, select the entire BEGIN through ROLLBACK block and execute together.
   The view exists only inside that transaction in this connection's temporary
   schema. For an interactive demonstration, execute BEGIN/CREATE/SELECT in order,
   inspect the result, and execute ROLLBACK before any other work.
5. For Q10, select its entire BEGIN through ROLLBACK block. The temporary table and
   its identity sequence are separate from application data. ON COMMIT DROP also
   removes the table if the demo is committed instead. Do not rename its DML target
   to the real categories table. Inspect each RETURNING result by running statements
   in order within the transaction, then finish with ROLLBACK.
6. If a demo statement fails while the transaction is open, execute `ROLLBACK;`
   before retrying the complete block. Both demos can then be run again.
7. Compare Q2–Q4 and Q6–Q7 with the web pages while no one is modifying data. Check
   zero cases and multiple rows per category, then follow testing_checklist.md.

To execute the whole script using psql from the project root:

```powershell
psql -h localhost -p 5432 -U postgres -d founddesk -v ON_ERROR_STOP=1 -f database/queries.sql
```

Flask does not need queries.sql installed to start. The script creates no lasting
view/table and never writes the application's five tables or identity sequences.
Phase 12: the script executed successfully against real PostgreSQL through psycopg
and installed psql. Actual output is in evidence/phase12/psql_queries_output.txt;
see local_integration_results.md. pgAdmin UI execution itself was not observed.
