-- Only category names are seeded; no users or passwords are included.
BEGIN;

INSERT INTO categories (category_name)
VALUES
    ('ID Cards'),
    ('Keys'),
    ('Electronics'),
    ('Books'),
    ('Accessories'),
    ('Other')
ON CONFLICT (category_name) DO NOTHING;

COMMIT;
