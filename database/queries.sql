-- Phase 10 teaching queries. Run AFTER schema.sql and sample_data.sql.
-- Q1-Q8 only read application tables. Q9-Q10 create temporary objects inside
-- rolled-back demo transactions; they never write application tables/sequences.
-- Run each demo BEGIN-through-ROLLBACK block together, not isolated DDL/DML lines.

-- Q1: SELECT / WHERE / ORDER BY: unresolved losses, newest event date first.
SELECT lost_id, item_name, location, lost_date
FROM lost_items WHERE status = 'Lost'
ORDER BY lost_date DESC, lost_id DESC;

-- Q2: meaningful COUNT totals; independent scalar subqueries avoid join fan-out.
SELECT (SELECT COUNT(*) FROM lost_items) AS lost_count,
       (SELECT COUNT(*) FROM found_items) AS found_count,
       (SELECT COUNT(*) FROM claims WHERE status = 'Pending') AS pending_count,
       (SELECT COUNT(*) FROM found_items WHERE status = 'Returned') AS returned_count;

-- Q3: GROUP BY / LEFT JOIN: retain categories with zero reports.
-- Pre-aggregate each side: joining raw lost AND found rows would multiply counts.
SELECT c.category_name, COALESCE(l.lost_count, 0) AS lost_count,
       COALESCE(f.found_count, 0) AS found_count
FROM categories AS c
LEFT JOIN (
    SELECT category_id, COUNT(*) AS lost_count FROM lost_items GROUP BY category_id
) AS l ON l.category_id = c.category_id
LEFT JOIN (
    SELECT category_id, COUNT(*) AS found_count FROM found_items GROUP BY category_id
) AS f ON f.category_id = c.category_id
ORDER BY c.category_name;

-- Q4: claim counts, including zero for a status with no claims.
-- COUNT(c.claim_id) ignores the NULL produced by an unmatched LEFT JOIN.
SELECT s.status, COUNT(c.claim_id) AS claim_count
FROM (VALUES ('Pending'), ('Approved'), ('Rejected')) AS s(status)
LEFT JOIN claims AS c ON c.status = s.status
GROUP BY s.status ORDER BY s.status;

-- Q5: HAVING: categories with at least two unresolved lost reports.
-- WHERE filters rows before grouping; HAVING filters completed groups.
SELECT c.category_name, COUNT(l.lost_id) AS unresolved_count
FROM categories AS c
INNER JOIN lost_items AS l ON l.category_id = c.category_id
WHERE l.status = 'Lost'
GROUP BY c.category_id, c.category_name
HAVING COUNT(l.lost_id) >= 2
ORDER BY unresolved_count DESC, c.category_name;

-- Q6: INNER JOIN: returned reports with readable categories, not return dates.
SELECT f.found_id, f.item_name, c.category_name, f.location, f.found_date
FROM found_items AS f
INNER JOIN categories AS c ON c.category_id = f.category_id
WHERE f.status = 'Returned' ORDER BY f.found_date DESC, f.found_id DESC;

-- Q7: multi-table INNER JOIN: unresolved items with readable category names.
SELECT l.lost_id, l.item_name, c.category_name, l.location, l.lost_date
FROM lost_items AS l
INNER JOIN categories AS c ON c.category_id = l.category_id
WHERE l.status = 'Lost' ORDER BY l.lost_date DESC, l.lost_id DESC;

-- Q8: correlated NOT EXISTS subquery: Available found reports with no Pending claim.
SELECT f.found_id, f.item_name, f.found_date
FROM found_items AS f
WHERE f.status = 'Available'
  AND NOT EXISTS (
      SELECT 1 FROM claims AS c WHERE c.found_id = f.found_id AND c.status = 'Pending'
  )
ORDER BY f.found_date DESC, f.found_id DESC;

-- Q9: CREATE VIEW demo. TEMP scopes the view to this connection, outside public.
-- The ROLLBACK also removes it immediately; Flask does not depend on this view.
BEGIN;
CREATE TEMP VIEW founddesk_unresolved_lost AS
SELECT l.lost_id, l.item_name, c.category_name, l.location, l.lost_date
FROM lost_items AS l
INNER JOIN categories AS c ON c.category_id = l.category_id
WHERE l.status = 'Lost';
SELECT * FROM founddesk_unresolved_lost ORDER BY lost_date DESC, lost_id DESC;
ROLLBACK;

-- Q10: INSERT / UPDATE / DELETE demo transaction on a TEMP category table only.
-- INCLUDING ALL copies constraints and creates a separate identity sequence.
-- No production row or production identity sequence is changed, even if committed.
BEGIN;
CREATE TEMP TABLE founddesk_demo_categories (LIKE categories INCLUDING ALL) ON COMMIT DROP;
INSERT INTO founddesk_demo_categories (category_name) VALUES ('Demo Stationery')
RETURNING category_id, category_name;
UPDATE founddesk_demo_categories SET category_name = 'Demo Books and Stationery'
WHERE category_name = 'Demo Stationery' RETURNING category_id, category_name;
DELETE FROM founddesk_demo_categories WHERE category_name = 'Demo Books and Stationery'
RETURNING category_id, category_name;
ROLLBACK;
