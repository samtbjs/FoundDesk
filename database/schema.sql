-- Run once in a new FoundDesk database, before sample_data.sql.
BEGIN;

CREATE TABLE users (
    user_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(10) NOT NULL DEFAULT 'student',
    CONSTRAINT users_role_check CHECK (role IN ('student', 'admin'))
);

CREATE TABLE categories (
    category_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE lost_items (
    lost_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    category_id INTEGER NOT NULL REFERENCES categories(category_id) ON DELETE RESTRICT,
    item_name VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR(200) NOT NULL,
    lost_date DATE NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'Lost',
    CONSTRAINT lost_items_status_check CHECK (status IN ('Lost', 'Resolved'))
);

CREATE TABLE found_items (
    found_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    category_id INTEGER NOT NULL REFERENCES categories(category_id) ON DELETE RESTRICT,
    item_name VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR(200) NOT NULL,
    found_date DATE NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'Available',
    CONSTRAINT found_items_status_check CHECK (status IN ('Available', 'Returned'))
);

CREATE TABLE claims (
    claim_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lost_id INTEGER NOT NULL REFERENCES lost_items(lost_id) ON DELETE RESTRICT,
    found_id INTEGER NOT NULL REFERENCES found_items(found_id) ON DELETE RESTRICT,
    claimant_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    claim_reason TEXT NOT NULL,
    claim_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(10) NOT NULL DEFAULT 'Pending',
    CONSTRAINT claims_status_check CHECK (status IN ('Pending', 'Approved', 'Rejected')),
    CONSTRAINT claims_item_pair_unique UNIQUE (lost_id, found_id)
);

COMMIT;
